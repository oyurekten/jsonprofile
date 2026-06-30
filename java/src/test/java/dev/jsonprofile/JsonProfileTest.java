package dev.jsonprofile;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class JsonProfileTest {
    @Test
    void exposesLibraryName() {
        assertEquals("jsonprofile", JsonProfile.name());
    }
}
