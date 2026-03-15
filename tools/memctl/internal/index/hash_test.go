package index

import "testing"

func TestFileHash(t *testing.T) {
	hash := HashBytes([]byte("hello world"))
	if len(hash) != 64 {
		t.Errorf("SHA256 hex should be 64 chars, got %d", len(hash))
	}
	// Known SHA256 of "hello world"
	want := "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
	if hash != want {
		t.Errorf("hash = %q, want %q", hash, want)
	}
}
