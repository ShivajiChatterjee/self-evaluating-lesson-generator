# Retrieval-Augmented Generation Reference

## What RAG is

Retrieval-Augmented Generation (RAG) combines a generative language model with information retrieved from an external knowledge source. At query time, the system finds relevant material and supplies it to the model as context for generating an answer.

## Why RAG is useful

A language model's built-in knowledge comes from its training data. That knowledge can be incomplete, outdated, or missing private and domain-specific information. A model can also produce plausible statements that are not supported by evidence.

RAG gives the model access to selected external information when answering. This can make responses more relevant, current, and traceable to source material. It does not guarantee correctness: answer quality still depends on the trustworthiness of the sources, retrieval quality, and how accurately the model uses the retrieved context.

## Basic RAG flow

1. A user submits a question or query.
2. The system retrieves relevant information from an external knowledge source.
3. The retrieved information is provided to the language model as context alongside the query.
4. The language model generates an answer using the query and retrieved context.

External knowledge sources may include curated documents, databases, knowledge bases, or APIs. Many RAG systems split documents into smaller passages and represent them as embeddings. An embedding is a numerical representation used to compare semantic similarity between a query and stored passages. Embeddings are a common retrieval method, but RAG is defined by using retrieved external context, not by one specific search technique.

## Retrieval context is not model training

Retrieved context is temporary input supplied for a particular request. Standard RAG does not retrain the model or permanently update its weights for every query. Updating the external source or its search index can change what the system retrieves without changing the language model itself. Fine-tuning or further model training may be used separately, but those are distinct from the normal retrieval-time RAG process.

## Sources

- [Lewis et al. (2020), *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*](https://arxiv.org/abs/2005.11401)
- [AWS, *Retrieval Augmented Generation - Amazon SageMaker AI*](https://docs.aws.amazon.com/sagemaker/latest/dg/jumpstart-foundation-models-customize-rag.html)
