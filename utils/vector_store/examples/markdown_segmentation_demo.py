#!/usr/bin/env python3
"""
Demonstration of comprehensive markdown segmentation and semantic search.

This script shows how to:
1. Segment markdown content into text chunks and tables
2. Split large tables into smaller chunks
3. Store all segments in a vector database
4. Perform semantic search to retrieve relevant segments
"""

import os
import sys
from pathlib import Path

# Add the project root to the path if needed
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from utils.vector_store.markdown_segmenter import MarkdownSegmenter

# Sample markdown content with text and tables, including a large table
SAMPLE_MARKDOWN = """
# Machine Learning Algorithm Comparison

## Introduction

Machine learning has revolutionized many industries by enabling computers to learn from data and make predictions or decisions without being explicitly programmed. This document compares various machine learning algorithms across different metrics and use cases.

## Supervised Learning Algorithms

Supervised learning algorithms learn from labeled training data to make predictions on new, unseen data. Here are some of the most commonly used supervised learning algorithms:

### Classification Algorithms

Classification algorithms are used to predict discrete class labels. They're widely used in applications like spam detection, sentiment analysis, and image classification.

| Algorithm | Strengths | Weaknesses | Typical Applications |
|-----------|----------|------------|---------------------|
| Logistic Regression | Simple, interpretable, works well with linearly separable data | Struggles with complex relationships, assumes linear decision boundary | Binary classification, risk assessment, credit scoring |
| Decision Trees | Intuitive, handles non-linear relationships, no feature scaling needed | Prone to overfitting, unstable (small changes in data can lead to different trees) | Customer segmentation, medical diagnosis, credit risk |
| Random Forest | Robust to overfitting, handles high-dimensional data, provides feature importance | Slower training than single trees, less interpretable | Image classification, fraud detection, recommendation systems |
| Support Vector Machines | Effective in high-dimensional spaces, memory efficient, versatile through kernels | Sensitive to feature scaling, computationally intensive for large datasets | Text categorization, image classification, bioinformatics |
| Naive Bayes | Fast, works well with high-dimensional data, effective with small training sets | Assumes feature independence (naive assumption), struggles with numeric features | Spam filtering, sentiment analysis, document classification |
| K-Nearest Neighbors | Simple, no training phase, naturally handles multi-class problems | Computationally expensive for large datasets, sensitive to irrelevant features | Recommendation systems, anomaly detection, pattern recognition |

### Regression Algorithms

Regression algorithms are used to predict continuous values. They're commonly used in forecasting, trend analysis, and relationship modeling.

| Algorithm | Strengths | Weaknesses | Typical Applications |
|-----------|----------|------------|---------------------|
| Linear Regression | Simple, interpretable, computationally efficient | Assumes linear relationship, sensitive to outliers | Price prediction, sales forecasting, trend analysis |
| Ridge Regression | Handles multicollinearity, reduces overfitting | Still assumes linearity, requires tuning of regularization parameter | Financial modeling, biological response modeling |
| Lasso Regression | Feature selection capability, handles multicollinearity | Still assumes linearity, can be unstable with correlated features | Feature selection, model simplification |
| Elastic Net | Combines strengths of Ridge and Lasso, handles correlated features | Requires tuning of multiple parameters | High-dimensional data analysis, genomics |
| Decision Tree Regression | Handles non-linear relationships, no feature scaling needed | Prone to overfitting, unstable | Complex non-linear relationships, environmental modeling |
| Random Forest Regression | Robust to overfitting, handles high-dimensional data | Slower training, less interpretable | Stock price prediction, demand forecasting |

## Unsupervised Learning Algorithms

Unsupervised learning algorithms find patterns in unlabeled data. They're used for clustering, dimensionality reduction, and anomaly detection.

### Clustering Algorithms

Clustering algorithms group similar data points together. They're useful for customer segmentation, image compression, and pattern discovery.

| Algorithm | Strengths | Weaknesses | Typical Applications |
|-----------|----------|------------|---------------------|
| K-Means | Simple, scalable, efficient | Requires number of clusters in advance, sensitive to initial centroids and outliers | Customer segmentation, image compression, document clustering |
| Hierarchical Clustering | No need to specify number of clusters, produces dendrogram visualization | Computationally intensive for large datasets, sensitive to outliers | Taxonomy creation, customer hierarchy analysis, genetic sequence analysis |
| DBSCAN | Finds arbitrarily shaped clusters, robust to outliers, no need to specify number of clusters | Struggles with varying density clusters, sensitive to parameters | Spatial data analysis, anomaly detection, noise removal |
| Mean Shift | No need to specify number of clusters, finds clusters of arbitrary shape | Computationally intensive, bandwidth selection can be challenging | Image segmentation, tracking objects, mode finding |
| Gaussian Mixture Models | Soft clustering (probability of belonging to each cluster), flexible cluster shapes | Sensitive to initialization, can converge to local optima | Image segmentation, speaker identification, financial modeling |
| Agglomerative Clustering | Intuitive, hierarchical structure, no need to specify number of clusters | Computationally intensive, cannot undo previous steps | Document clustering, genetic analysis, social network analysis |

## Deep Learning Algorithms

Deep learning algorithms use neural networks with multiple layers to learn representations of data. They've achieved remarkable success in various domains, especially with large datasets.

| Architecture | Strengths | Weaknesses | Typical Applications |
|--------------|----------|------------|---------------------|
| Feedforward Neural Networks | Versatile, can approximate any function, handles non-linear relationships | Requires large training data, prone to overfitting, black-box nature | Pattern recognition, classification, regression |
| Convolutional Neural Networks (CNNs) | Excellent for spatial data, parameter sharing reduces overfitting | Computationally intensive, requires large training data | Image recognition, video analysis, medical image processing |
| Recurrent Neural Networks (RNNs) | Handles sequential data, maintains memory of previous inputs | Vanishing/exploding gradient problems, computationally intensive | Natural language processing, time series prediction, speech recognition |
| Long Short-Term Memory (LSTM) | Solves vanishing gradient problem, better at capturing long-term dependencies | Complex architecture, computationally intensive | Machine translation, speech recognition, text generation |
| Generative Adversarial Networks (GANs) | Generates realistic synthetic data, unsupervised learning | Training instability, mode collapse, difficult to evaluate | Image generation, data augmentation, style transfer |
| Transformers | Excellent for sequential data, handles long-range dependencies, parallelizable | Memory intensive, requires large training data | Natural language processing, machine translation, question answering |
| Autoencoders | Unsupervised feature learning, dimensionality reduction | Can learn trivial solutions without constraints, training challenges | Anomaly detection, image denoising, feature extraction |
| Graph Neural Networks | Handles graph-structured data, captures node relationships | Scalability challenges with large graphs, limited theoretical understanding | Social network analysis, molecular structure prediction, recommendation systems |

## Algorithm Selection Guidelines

Choosing the right algorithm depends on several factors:

1. **Problem type**: Classification, regression, clustering, etc.
2. **Data size and quality**: Some algorithms work better with large datasets, others with small ones
3. **Interpretability requirements**: Some applications need transparent models
4. **Training and inference time constraints**: Real-time applications have strict latency requirements
5. **Feature characteristics**: High-dimensional data, sparse features, etc.

Always consider starting with simpler models before moving to more complex ones, and use cross-validation to evaluate performance.

## Performance Metrics

### Classification Metrics

| Metric | Description | When to Use |
|--------|------------|------------|
| Accuracy | Proportion of correct predictions | Balanced datasets |
| Precision | True positives / (True positives + False positives) | When false positives are costly |
| Recall | True positives / (True positives + False negatives) | When false negatives are costly |
| F1 Score | Harmonic mean of precision and recall | Balanced view of precision and recall |
| ROC AUC | Area under ROC curve | Ranking quality and threshold-invariant evaluation |
| Confusion Matrix | Table showing prediction errors and types | Detailed error analysis |

### Regression Metrics

| Metric | Description | When to Use |
|--------|------------|------------|
| Mean Absolute Error (MAE) | Average absolute differences | When outliers should not have extra influence |
| Mean Squared Error (MSE) | Average squared differences | When large errors should be penalized more |
| Root Mean Squared Error (RMSE) | Square root of MSE | Same as MSE but in original units |
| R² (R-squared) | Proportion of variance explained by the model | General goodness of fit |
| Adjusted R² | R² adjusted for number of predictors | Comparing models with different numbers of features |
| Mean Absolute Percentage Error (MAPE) | Average percentage difference | For relative error importance |

## Conclusion

Machine learning algorithm selection is both an art and a science. Understanding the strengths and weaknesses of different algorithms helps in choosing the most appropriate one for a specific problem. Always experiment with multiple algorithms and use cross-validation to find the best performer for your particular use case.
"""


def main():
    """Run the markdown segmentation and search demonstration."""
    # Initialize the markdown segmenter with in-memory database
    segmenter = MarkdownSegmenter(
        collection_name="ml_algorithms",
        chunk_size=500,  # Smaller chunks for demonstration
        chunk_overlap=100,
        table_max_rows=5,  # Small value to demonstrate table splitting
    )

    print("Using in-memory vector database")

    # Segment and store markdown content
    num_segments, segment_ids = segmenter.segment_and_store(SAMPLE_MARKDOWN)
    print(f"Segmented and stored {num_segments} segments:")
    print(f"  - Text segments: {len(segment_ids['text'])}")
    print(f"  - Table segments: {len(segment_ids['table'])}")

    # Show the segmentation results
    segments = segmenter.segment_markdown(SAMPLE_MARKDOWN)

    # Display text segments
    text_segments = [s for s in segments if s["type"] == "text"]
    print(f"\n=== Text Segments ({len(text_segments)}) ===")
    for i, segment in enumerate(text_segments[:3]):  # Show first 3 for brevity
        print(f"\nText Segment {i+1}:")
        if segment["heading"]:
            print(f"Heading: {segment['heading']}")
        print("-" * 50)
        print(
            segment["content"][:150] + "..."
            if len(segment["content"]) > 150
            else segment["content"]
        )
        print("-" * 50)

    if len(text_segments) > 3:
        print(f"... and {len(text_segments) - 3} more text segments")

    # Display table segments
    table_segments = [s for s in segments if s["type"] == "table"]
    print(f"\n=== Table Segments ({len(table_segments)}) ===")

    # Group table chunks by parent ID
    table_groups = {}
    for segment in table_segments:
        parent_id = segment.get("parent_id", segment["id"])
        if parent_id not in table_groups:
            table_groups[parent_id] = []
        table_groups[parent_id].append(segment)

    # Sort chunks within each group
    for parent_id in table_groups:
        table_groups[parent_id].sort(key=lambda x: x.get("chunk_index", 0))

    # Display information about each table group
    for i, (parent_id, chunks) in enumerate(
        list(table_groups.items())[:3]
    ):  # Show first 3 tables
        print(f"\nTable {i+1}:")
        if chunks[0]["heading"]:
            print(f"Heading: {chunks[0]['heading']}")
        print(f"Number of chunks: {len(chunks)}")

        # Show the first chunk of each table
        first_chunk = chunks[0]
        print("-" * 50)
        print(first_chunk["content"])
        if len(chunks) > 1:
            print("\n... (table continues in additional chunks) ...")
        print("-" * 50)

    if len(table_groups) > 3:
        print(f"... and {len(table_groups) - 3} more tables")

    # Perform semantic searches
    search_queries = [
        "What are the strengths of convolutional neural networks?",
        "Which algorithm is best for image classification?",
        "How do you evaluate regression models?",
        "What are the weaknesses of clustering algorithms?",
        "Which algorithms work well with small datasets?",
    ]

    print("\n=== Semantic Search Results ===")
    for query in search_queries:
        print(f"\nQuery: {query}")

        # Search across all segment types
        results = segmenter.search(query, n_results=2)

        for i, (doc, metadata, distance) in enumerate(
            zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ):
            similarity = 1 - distance
            print(
                f"\nResult {i+1} (similarity: {similarity:.4f}, type: {metadata['type']}):"
            )
            if metadata["heading"]:
                print(f"Heading: {metadata['heading']}")

            print("-" * 50)
            # For tables, show the whole content; for text, limit to first 200 chars
            if metadata["type"] == "table":
                print(doc)
                if metadata.get("is_chunk", False):
                    print(
                        f"(Chunk {metadata['chunk_index'] + 1} of {metadata['total_chunks']})"
                    )
            else:
                print(doc[:200] + "..." if len(doc) > 200 else doc)
            print("-" * 50)


if __name__ == "__main__":
    main()
