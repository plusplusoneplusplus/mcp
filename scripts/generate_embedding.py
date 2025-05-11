from transformers import AutoTokenizer, AutoModel
import torch

# Load the model and tokenizer
# model_name = "microsoft/phi-4"
model_name = "microsoft/Phi-4-mini-instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Set up device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = AutoModel.from_pretrained(model_name).to(device)


def generate_embedding(text, max_length=512):
    # Tokenize the input text
    inputs = tokenizer(
        text, return_tensors="pt", padding=True, truncation=True, max_length=max_length
    )

    # Move inputs to GPU
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Generate embeddings
    with torch.no_grad():
        outputs = model(**inputs)

        # Get all token embeddings
        token_embeddings = outputs.last_hidden_state[0]

        # Mean pooling
        mask = inputs["attention_mask"][0]
        mask_expanded = mask.unsqueeze(-1).expand(token_embeddings.size())
        sum_embeddings = torch.sum(token_embeddings * mask_expanded, 0)
        sum_mask = torch.clamp(mask_expanded.sum(0), min=1e-9)
        embeddings = sum_embeddings / sum_mask

        # Normalize
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=0)

    return embeddings.cpu()  # Return tensor on CPU for further processing if needed


# Example usage
if __name__ == "__main__":
    text = "def hello_world():\n    print('Hello, World!')"
    embedding = generate_embedding(text)
    print(f"Embedding shape: {embedding.shape}")
