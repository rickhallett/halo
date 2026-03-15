package index

import (
	"crypto/sha256"
	"fmt"
	"os"
)

func HashBytes(data []byte) string {
	h := sha256.Sum256(data)
	return fmt.Sprintf("%x", h)
}

func HashFile(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return HashBytes(data), nil
}
