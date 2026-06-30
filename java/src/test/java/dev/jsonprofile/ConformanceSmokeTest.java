package dev.jsonprofile;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class ConformanceSmokeTest {
    @Test
    void sharedConformanceManifestLoads() throws Exception {
        Path manifestPath = Path.of("..", "shared", "conformance", "smoke.json");
        JsonNode manifest = new ObjectMapper().readTree(manifestPath.toFile());

        assertEquals("0.1.0", manifest.get("version").asText());
        assertEquals(2, manifest.get("cases").size());
        assertTrue(manifest.get("cases").findValuesAsText("id").contains("minimal-valid-profile"));
        assertTrue(manifest.get("cases").findValuesAsText("id").contains("missing-required-profile-name"));
    }
}
