import logging
import re
from typing import Any, Generic, TypeVar
from urllib.parse import quote

import bioregistry
import httpx2
import orjson
from cachetools import TTLCache, cached
from pydantic import field_validator

from jsonprofile.profile.base import CvTerm, JsonProfileBaseModel
from jsonprofile.validator.base import CvTermSearch

logger = logging.getLogger(__name__)

_T = TypeVar("T")


class _OlsSearchModel(JsonProfileBaseModel, Generic[_T]):
    page: int
    num_elements: int
    total_pages: int
    total_elements: int
    elements: list[_T]


class _ChildrenSearchModel(JsonProfileBaseModel):
    curie: str
    has_hierarchical_children: bool
    has_direct_children: bool
    iri: str
    is_obsolete: bool
    label: str
    ontology_preferred_prefix: str

    @field_validator("label", mode="before")
    @classmethod
    def label_validator(cls, value: list[str] | Any | None) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return value[0] if value else ""
        return str(value)


@cached(
    key=lambda url, params, headers, *args, **kwargs: (
        url,
        orjson.dumps(params, orjson.OPT_SORT_KEYS),
        orjson.dumps(headers, orjson.OPT_SORT_KEYS),
    ),
    cache=TTLCache(maxsize=2048, ttl=600),
)
def _search_ols(
    url: str, params: dict, headers: dict, timeout: int = 10
) -> tuple[int, dict[str, Any]]:
    try:
        result = httpx2.get(url, params=params, headers=headers, timeout=timeout)
        if result.status_code in {200, 201}:
            return result.status_code, result.json()
    except Exception as ex:
        return 500, {"error": str(ex)}
    logger.warning(
        "Could not find CV term: %s %s",
        result.status_code,
        orjson.dumps(params, orjson.OPT_SORT_KEYS),
    )
    return result.status_code, {}


class OlsCvTermSearch(CvTermSearch):
    def __init__(self) -> None:
        self.cache: dict[str, None | dict[str, CvTerm]] = {}
        self.search_cache: dict[str, tuple[bool, str | None]] = {}
        self.cv_term_cache: dict[str, None | CvTerm] = {}

    def get_curie(self, cv_term: CvTerm) -> None | str:
        if not cv_term or not cv_term.cv_accession:
            return None
        curie = cv_term.cv_accession
        if curie and (
            curie.startswith("http://") or cv_term.cv_accession.startswith("https://")
        ):
            curie = bioregistry.curie_from_iri(cv_term.cv_accession)

        return curie or None

    def get_children(
        self,
        cv_term: CvTerm,
        allow_only_leaf: bool = True,
        excluded_cv_accessions: None | list[str] = None,
        recursive: bool = False,
    ) -> list[CvTerm]:
        children: list[_ChildrenSearchModel] = []
        self.find_children_cv_terms(
            cv_term=cv_term,
            children=children,
            allow_only_leaf=allow_only_leaf,
            excluded_cv_accessions=excluded_cv_accessions,
            recursive=recursive,
        )
        cv_terms = [
            CvTerm(
                cv_label=x.ontology_preferred_prefix,
                cv_accession=x.curie,
                name=x.label,
            )
            for x in children
        ]
        return cv_terms

    def find_children_cv_terms(
        self,
        cv_term: CvTerm,
        children: list[_ChildrenSearchModel],
        allow_only_leaf: bool = True,
        excluded_cv_accessions: None | list[str] = None,
        recursive: bool = False,
    ) -> None:
        parent_uri = self.get_iri(cv_term)

        parent_uri_encoded = quote(quote(parent_uri, safe=[]))
        source = cv_term.cv_label.lower()
        children_subpath = f"/ontologies/{source}/classes/{parent_uri_encoded}/children"
        ols4_base_url = "https://www.ebi.ac.uk/ols4/api/v2"

        url = ols4_base_url + children_subpath
        page = 0
        finished = False
        headers = {"Accept": "application/json"}
        selected_terms: list[_ChildrenSearchModel] = []
        while not finished:
            params = {"page": page, "size": 100}
            page += 1
            _, result_json = _search_ols(url, params, headers, timeout=10)
            if not result_json:
                logger.warning(
                    "Could not find children CV Terms for %s - %s",
                    cv_term.cv_accession,
                    cv_term.name,
                )
                break
            search = _OlsSearchModel[_ChildrenSearchModel].model_validate(result_json)
            selected_items = [x for x in search.elements if not x.is_obsolete]
            selected = []
            if excluded_cv_accessions:
                for x in selected_items:
                    for pattern in excluded_cv_accessions:
                        if not re.match(pattern, x):
                            selected.append(x)

            if selected:
                selected_terms.extend(selected)
            if page >= search.total_pages:
                finished = True
        for term in selected_terms:
            if not allow_only_leaf or (
                allow_only_leaf and not term.has_hierarchical_children
            ):
                children.append(term)

            if term.has_hierarchical_children and recursive:
                self.find_children_cv_terms(
                    cv_term=CvTerm(
                        accession=term.curie,
                        name=term.label,
                        source=term.ontology_preferred_prefix,
                    ),
                    children=children,
                    allow_only_leaf=allow_only_leaf,
                    excluded_cv_accessions=excluded_cv_accessions,
                    recursive=recursive,
                )

    def get_iri(self, cv_term: CvTerm) -> str | None:
        if cv_term.cv_accession and (
            cv_term.cv_accession.startswith("http://")
            or cv_term.cv_accession.startswith("https://")
        ):
            return cv_term.cv_accession
        uri = None
        if cv_term and ":" in cv_term.cv_accession:
            prefix, identifier = cv_term.cv_accession.split(":")
            uri = bioregistry.get_default_iri(prefix, identifier)
            if uri and isinstance(uri, str) and "iri=" in uri:
                return uri.split("iri=")[-1]

        return uri or None

    def find_cv_term_with_accession(
        self, source: str, accession: str
    ) -> tuple[CvTerm, list[str]]:
        curie = accession
        if accession and (
            accession.startswith("http://") or accession.startswith("https://")
        ):
            curie = bioregistry.curie_from_iri(accession)

        params = {
            "q": curie.lower(),
            "ontology": source.lower(),
            "type": "class,property,individual",
            "exact": True,
            "format": "json",
            "start": 0,
            "rows": 1,
            "local": False,
            "obsoletes": False,
            "lang": "en",
        }

        params["queryFields"] = "obo_id,iri,short_form"
        params["fieldList"] = "iri,obo_id,label,short_form,ontology_prefix,synonym"
        children_subpath = "/search"
        ols4_base_url = "https://www.ebi.ac.uk/ols4/api"
        url = ols4_base_url + children_subpath

        headers = {"Accept": "application/json"}
        try:
            logger.debug("Searching %s: %s in %s ontology", url, curie, source)
            status_code, result_json = _search_ols(url, params, headers, timeout=10)
            if status_code == 404:
                return None, []
            docs = result_json.get("response", {}).get("docs")
            if not docs:
                return None, []
            label = docs[0].get("label", "")
            synonym = docs[0].get("synonym", []) or []
            return CvTerm(
                accession=accession,
                name=label,
                source=source,
            ), synonym
        except Exception as ex:
            logger.exception(ex)
            return None, []

    def find_cv_term(
        self,
        source: str,
        accession_or_label: str,
        matched_accession: None | str = None,
        allow_synonym_search: bool = False,
    ) -> None | CvTerm:
        key = (source, accession_or_label, matched_accession, allow_synonym_search)
        if key in self.cv_term_cache and self.cv_term_cache[key]:
            return self.cv_term_cache[key]
        if not source or not accession_or_label:
            raise ValueError("Source and accession_or_label must be provided")
        search_by_accession = None
        is_accession_input = len(accession_or_label.split(":")) == 2
        if matched_accession:
            search_by_accession = matched_accession
        if not search_by_accession and is_accession_input:
            search_by_accession = accession_or_label

        if search_by_accession:
            term_result, synonym = self.find_cv_term_with_accession(
                source=source, accession=search_by_accession
            )
            if term_result:
                if is_accession_input:
                    if key not in self.cache or not self.cv_term_cache[key]:
                        self.cv_term_cache[key] = term_result
                    return term_result
                else:
                    if (
                        term_result.name.lower() == accession_or_label.lower()
                        or accession_or_label.lower() in {x.lower() for x in synonym}
                    ):
                        if key not in self.cv_term_cache or not self.cv_term_cache[key]:
                            self.cv_term_cache[key] = term_result
                        return term_result

        label = accession_or_label.strip().lower()
        params = {
            "q": label,
            "ontology": source.lower(),
            "type": "class,property,individual",
            "exact": True,
            "format": "json",
            "start": 0,
            "rows": 1,
            "local": False,
            "obsoletes": False,
            "lang": "en",
            # "isLeaf": (
            #     True if parent_cv_term and parent_cv_term.allow_only_leaf else False
            # ),
        }
        if allow_synonym_search:
            params["queryFields"] = "obo_id,iri,label,short_form,synonym"
            params["fieldList"] = "iri,obo_id,label,short_form,ontology_prefix,synonym"
        else:
            params["queryFields"] = "obo_id,iri,label,short_form"
            params["fieldList"] = "iri,obo_id,label,short_form,ontology_prefix"

        children_subpath = "/search"
        ols4_base_url = "https://www.ebi.ac.uk/ols4/api"
        url = ols4_base_url + children_subpath

        headers = {"Accept": "application/json"}
        try:
            logger.debug("Searching %s: %s in %s ontology", url, label, source)
            status_code, result_json = _search_ols(url, params, headers, timeout=10)
            if status_code == 404:
                self.search_cache[key] = None
                return self.search_cache[key]
            docs = result_json.get("response", {}).get("docs")
            if docs:
                obo_id = docs[0].get("obo_id", "")
                iri = docs[0].get("iri", "")
                label = docs[0].get("label", "")
                # synonyms = docs[0].get("synonym", [])
                ontology_prefix = docs[0].get("ontology_prefix", "").lower()
                if ontology_prefix != source.lower():
                    logger.warning(
                        "CV Term %s not found in %s", accession_or_label, source
                    )
                    return None
                uppercase_source = source.upper()
                if obo_id == label:
                    result_source = uppercase_source
                else:
                    result_source = (
                        ontology_prefix.upper() or obo_id.split(":")[0].upper()
                    )
                    if obo_id.upper() == result_source.upper():
                        result_source = uppercase_source
                if ":" in obo_id:
                    result_accession = obo_id
                else:
                    result_accession = iri
                term = CvTerm(
                    accession=result_accession,
                    name=label,
                    source=result_source,
                )
                if key not in self.cv_term_cache or not self.cv_term_cache[key]:
                    self.cv_term_cache[key] = term
                return term
        except Exception as ex:
            logger.exception(str(ex))
            return None

    def check_cv_term(
        self,
        cv_term: CvTerm,
        parent_cv_term: None | CvTerm = None,
        allow_synonym_search: bool = False,
    ) -> tuple[bool, str]:
        if not cv_term.cv_accession or not cv_term.name or not cv_term.cv_label:
            message = f"Invalid cv term {cv_term}"
            logger.error(message)
            return False, message
        if not parent_cv_term:
            term = self.find_cv_term(
                cv_term.cv_label,
                cv_term.cv_accession,
                allow_synonym_search=allow_synonym_search,
            )
            if not term:
                return False, f"CV term {cv_term.cv_accession} not found"
            return True, ""
        if parent_cv_term:
            if (
                not parent_cv_term.cv_accession
                or not parent_cv_term.name
                or not parent_cv_term.cv_label
            ):
                message = f"Invalid cv term parent {parent_cv_term}"
                logger.error(message)
                return False, message

        key = ",".join([str(cv_term), str(parent_cv_term), str(allow_synonym_search)])

        if key in self.search_cache:
            return self.search_cache[key]

        children_subpath = "/search"
        if parent_cv_term:
            logger.debug(
                "Check CV term %s - %s whether is child of %s %s",
                cv_term.cv_accession,
                cv_term.name,
                parent_cv_term.cv_accession,
                parent_cv_term.name,
            )
        else:
            logger.debug("Check CV term %s - %s", cv_term.cv_accession, cv_term.name)

        accession = cv_term.cv_accession
        search_ontology = (cv_term.cv_label or "").lower()
        params = {
            "q": accession.lower(),
            "type": "class,property,individual",
            "exact": True,
            "start": 0,
            "obsoletes": False,
            "rows": 1,
            # "local": False,
            "format": "json",
            "lang": "en",
            # "isLeaf": (
            #     True if parent_cv_term and parent_cv_term.allow_only_leaf else False
            # ),
        }

        if allow_synonym_search:
            params["queryFields"] = "obo_id,short_form,iri,synonym"
            params["fieldList"] = "iri,obo_id,label,short_form,ontology_prefix,synonym"
        else:
            params["queryFields"] = "obo_id,short_form,iri"
            params["fieldList"] = "iri,obo_id,label,short_form,ontology_prefix"
        if search_ontology:
            params["ontology"] = search_ontology

        ols4_base_url = "https://www.ebi.ac.uk/ols4/api"
        url = ols4_base_url + children_subpath
        parent_uri = self.get_iri(parent_cv_term)
        params["allChildrenOf"] = parent_uri
        logger.debug(
            "%s: %s in cv %s, parent %s",
            url,
            accession,
            cv_term.cv_label,
            parent_uri,
        )

        headers = {"Accept": "application/json"}
        try:
            logger.debug("Searching %s", url)
            status_code, result_json = _search_ols(url, params, headers, timeout=10)
            if status_code == 404:
                self.search_cache[key] = (
                    False,
                    f"{cv_term.cv_label} is not valid or "
                    f"{accession} is not in ontology {cv_term.cv_label}",
                )
                return self.search_cache[key]
            docs = result_json.get("response", {}).get("docs")
            if docs:
                obo_id = docs[0].get("obo_id", "")
                iri_id = docs[0].get("iri", "")
                synonyms = docs[0].get("synonym", []) or []
                synonyms_lower_set = {s.lower() for s in synonyms}
                if accession.lower() in {obo_id.lower(), iri_id.lower()} and (
                    docs[0].get("label", "").lower() == cv_term.name.lower()
                    or (
                        allow_synonym_search
                        and cv_term.name.lower() in synonyms_lower_set
                    )
                ):
                    if parent_cv_term:
                        logger.debug(
                            "CV term with %s %s is child of %s %s",
                            cv_term.cv_accession,
                            cv_term.name,
                            (parent_cv_term.cv_accession if parent_cv_term else None),
                            parent_cv_term.name if parent_cv_term else None,
                        )
                    else:
                        logger.debug(
                            "CV term with %s and %s is valid CV term",
                            accession,
                            cv_term.name,
                        )
                    self.search_cache[key] = (True, None)
                    return self.search_cache[key]
                if not parent_cv_term:
                    self.search_cache[key] = (
                        False,
                        f"'{cv_term.cv_label}' is not valid source or "
                        f"{cv_term} is not found "
                        f"in {cv_term.cv_label} ontology",
                    )
                else:
                    self.search_cache[key] = (
                        False,
                        f"{cv_term.name} {accession} is not child of "
                        f"{parent_cv_term.cv_accession} "
                        f"on source {parent_cv_term.cv_label}.",
                    )
                return self.search_cache[key]

            else:
                self.search_cache[key] = (False, f"{accession} does not match")
                return self.search_cache[key]

        except httpx2.HTTPStatusError as ex:
            return False, f"{accession} search failed: {str(ex)}"
        except Exception as ex:
            return (
                False,
                f"{accession} is not in {cv_term.cv_label} ontology. {str(ex)}",
            )
