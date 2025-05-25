# Sample Documents for GraphRAG Example

This folder contains sample documents used by the `basic_example.py` script to demonstrate GraphRAG functionality.

## Documents

- **`artificial_intelligence.txt`** - Overview of AI, machine learning, and deep learning technologies
- **`climate_change.txt`** - Information about climate change impacts, mitigation, and adaptation strategies  
- **`digital_transformation.txt`** - Discussion of digital transformation accelerated by the COVID-19 pandemic
- **`renewable_energy.txt`** - Comprehensive overview of renewable energy technologies and their integration
- **`blockchain_technology.txt`** - Detailed exploration of blockchain, cryptocurrencies, and decentralized applications
- **`space_exploration.txt`** - Modern space exploration including commercial spaceflight and Mars missions
- **`biotechnology.txt`** - Gene editing, synthetic biology, and biotechnology applications in medicine and agriculture
- **`quantum_computing.txt`** - Quantum computing principles, technologies, and potential applications
- **`cybersecurity.txt`** - Cybersecurity threats, defense strategies, and emerging security challenges
- **`sustainable_agriculture.txt`** - Sustainable farming practices, precision agriculture, and food system innovations

## Usage

These documents are automatically loaded by the basic example script when you run:

```bash
python basic_example.py
```

You can replace these files with your own documents to test GraphRAG with different content. The system supports text files and will process them to build a knowledge graph for querying.

## File Format

- Files should be in plain text format (`.txt`)
- UTF-8 encoding is recommended
- No specific length requirements, but larger documents will take longer to process

## Testing Coverage

The expanded fixture set now covers diverse domains including:
- Technology (AI, blockchain, quantum computing, cybersecurity)
- Science (biotechnology, space exploration)
- Environment (climate change, renewable energy, sustainable agriculture)
- Society (digital transformation)

This variety provides rich content for testing GraphRAG's ability to:
- Extract entities and relationships across different domains
- Build comprehensive knowledge graphs
- Answer complex queries spanning multiple topics
- Demonstrate cross-domain connections and insights 