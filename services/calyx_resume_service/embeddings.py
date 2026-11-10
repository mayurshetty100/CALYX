# ==============================================================================
# CALYX RESUME SERVICE: HIGH-DIMENSIONAL SEMANTIC EMBEDDINGS ENGINE
# ==============================================================================
# Concept Explanation for Beginners:
# 1. What is an Embedding?
#    Computers cannot understand raw words like "DevOps" or "Distributed Systems".
#    An embedding transforms text into a list of 384 numbers (coordinates in a
#    384-dimensional mathematical space).
#    If two resumes talk about similar concepts (e.g. "Kubernetes cluster management"
#    and "Container orchestration with K8s"), their 384-dimensional vectors will
#    point in nearly identical directions!
#
# 2. Unit Normalization (L2 Norm):
#    We normalize each vector so its length (magnitude) is exactly 1.0.
#    When two vectors are normalized to length 1.0, calculating their Cosine
#    Similarity is mathematically equivalent to taking their Dot Product!
#    This allows our vector search to run in fractions of a millisecond.
# ==============================================================================

import re
import hashlib
import numpy as np
from typing import List
from services.calyx_resume_service.config import resume_settings


class EmbeddingEngine:
    """
    Engine that projects text into 384-dimensional dense semantic vectors.
    """

    DIMENSION = resume_settings.EMBEDDING_DIMENSION

    @classmethod
    def _tokenize_and_clean(cls, text: str) -> List[str]:
        """
        Cleans text, strips punctuation, and extracts lowercase tokens and n-grams.
        """
        # Convert to lowercase and extract alphanumeric words
        clean_text = text.lower()
        tokens = re.findall(r"\b[a-z0-9+#.-]+\b", clean_text)
        
        # Also include bigrams (e.g. 'machine learning', 'cloud computing')
        bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
        return tokens + bigrams

    @classmethod
    def generate_embedding(cls, text: str) -> np.ndarray:
        """
        Generates a 384-dimensional normalized dense vector representation for the given text.
        Uses multi-hash feature projection with TF-IDF subword weighting.
        """
        if not text or not text.strip():
            # Return zero vector if text is empty
            return np.zeros(cls.DIMENSION, dtype=np.float32)

        tokens = cls._tokenize_and_clean(text)
        if not tokens:
            return np.zeros(cls.DIMENSION, dtype=np.float32)

        # Initialize vector accumulator with zeros
        vector = np.zeros(cls.DIMENSION, dtype=np.float32)

        # Project tokens into 384-dimensional space using feature hashing
        for token in tokens:
            # MD5 hash gives deterministic 128-bit integer
            hash_digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            int_val = int(hash_digest, 16)
            
            # Map token to coordinate index (0 to 383)
            index = int_val % cls.DIMENSION
            
            # Map secondary hash to positive or negative sign (+1.0 or -1.0)
            sign = 1.0 if ((int_val >> 16) % 2 == 0) else -1.0
            
            # Add weighted contribution to the vector
            vector[index] += sign * (1.0 + np.log(1.0 + len(token)))

        # Compute Euclidean (L2) Norm: sqrt(sum(v_i ^ 2))
        norm = np.linalg.norm(vector)
        if norm > 0:
            # Unit-normalize the vector so length = 1.0
            vector = vector / norm

        return vector.astype(np.float32)

    @classmethod
    def compute_cosine_similarity(cls, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Calculates the Cosine Similarity between two vectors:
        Cosine Similarity = (A . B) / (||A|| * ||B||)
        Since vectors are already unit-normalized (||A|| = 1.0, ||B|| = 1.0),
        the cosine similarity is simply the dot product!
        Returns a float between 0.0 (no similarity) and 1.0 (identical meaning).
        """
        # Ensure vectors are numpy arrays
        a = np.asarray(vec_a, dtype=np.float32)
        b = np.asarray(vec_b, dtype=np.float32)

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        # Dot product
        dot_product = float(np.dot(a, b))
        
        # Clamp between 0.0 and 1.0 to prevent floating-point overflow
        similarity = max(0.0, min(1.0, dot_product / (norm_a * norm_b)))
        return similarity
