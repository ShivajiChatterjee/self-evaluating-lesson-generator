# Retrieval-Augmented Generation Reference

## What RAG is

Retrieval-Augmented Generation (RAG) combines information retrieval with a generative language model. When a user submits a query, the system finds relevant material in an external knowledge source and supplies that material to the model as grounding context for its answer.

## Why RAG is useful

A language model's built-in knowledge comes from its training data. That knowledge can be incomplete, outdated, or missing private and domain-specific information. A model can also produce plausible statements that are not supported by evidence.

RAG gives the model selected external information when answering. This can make responses more relevant to a specific need, provide access to newer or private information, and make answers traceable through citations to source material. RAG does not guarantee correctness.

## Preparing knowledge for retrieval

External knowledge can come from curated documents, databases, knowledge bases, or APIs. A common preparation process divides documents into smaller passages, often called chunks, and stores them in an index designed for efficient searching. Useful source metadata, such as a document title or URL, can also be stored so the application can cite where retrieved information came from.

An index may support keyword, semantic, vector, or hybrid search. Vector search commonly uses embeddings. An embedding is a numerical representation of content. Embeddings allow a system to compare a query with stored passages by semantic similarity, which means similarity in meaning rather than only exact matching words. Embeddings are a common retrieval method, but RAG can use other search methods because its defining feature is retrieved external context, not one specific search technique.

## Basic RAG flow

RAG is often described as a retrieve-augment-generate process:

1. **Retrieve:** The application uses the user's query to find relevant passages in an index or other data store.
2. **Augment:** The application combines the query and retrieved passages in the input sent to the language model.
3. **Generate:** The model produces an answer using the query, its instructions, and the supplied grounding context. The application may also include citations using stored source metadata.

The retriever and generator have different roles. The retriever selects useful external content. The generator turns the query and that content into a readable response. The retrieved passages must be relevant and contain enough information to support the response.

## Retrieval context is not model training

Retrieved context is temporary input supplied for a particular request. Standard RAG does not retrain the model or permanently update its weights for every query. Updating the external source or its search index can change what the system retrieves without changing the language model itself. Fine-tuning or further model training may be used separately, but those are distinct from the normal retrieval-time RAG process.

## Quality and limitations

RAG quality depends on the full pipeline. Trustworthy source material, useful passage boundaries, an effective index, relevant retrieval, and clear instructions all affect the result. If retrieval returns irrelevant or incomplete passages, the generated answer can still be incomplete, off-topic, or inaccurate. Even with relevant grounding, a model can fail to use it correctly, so evaluation remains important.

Retrieved passages also consume part of the model's input capacity. A system may need to rank and select the most useful passages instead of providing every available document. Retrieval adds processing time and can add cost compared with a model-only request.

## Sources

- Lewis et al. — [*Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*](https://arxiv.org/abs/2005.11401)
- Microsoft Learn — [*Retrieval augmented generation (RAG) and indexes*](https://learn.microsoft.com/en-us/azure/foundry/concepts/retrieval-augmented-generation)
- Amazon Web Services — [*Retrieval Augmented Generation - Amazon SageMaker AI*](https://docs.aws.amazon.com/sagemaker/latest/dg/jumpstart-foundation-models-customize-rag.html)
- Google Cloud — [*What is Retrieval-Augmented Generation (RAG)?*](https://cloud.google.com/use-cases/retrieval-augmented-generation)
