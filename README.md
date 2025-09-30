# CCIP - Cross-Cultural Intelligence Profile

Generate detailed Excel reports based on survey data with embedded visual elements like radar charts and icons.

## Features

- **Deterministic Processing**: Ensures reproducibility and clarity in outputs
- **Visual Reports**: Embedded radar charts and icons in Excel
- **Multiple Dimensions**: Analyzes 5 key cross-cultural intelligence dimensions
- **Web Interface**: Simple Streamlit UI for file upload and processing

## Dimensions Analyzed

- **DT**: Directness & Transparency
- **TR**: Task vs Relational Accountability  
- **CO**: Conflict Orientation
- **CA**: Cultural Adaptability
- **EP**: Empathy & Perspective-Taking

## Quick Start

### Local Development

```bash
# Clone the repository
git clone <your-repo-url>
cd ccip

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run CLI
python -m ccip --input sample.csv --output results.xlsx

# Run web interface
streamlit run app.py
```

### Docker

```bash
# Build and run
docker build -t ccip .
docker run -p 8501:8501 ccip
```

Then open http://localhost:8501 in your browser.

## Usage

### Command Line
```bash
python -m ccip --input survey_data.xlsx --output results.xlsx
```

### Web Interface
1. Upload your survey Excel/CSV file
2. Click "Process Survey Data"
3. Download the generated CCIP report

## Input Format

Your input file should contain:
- Survey responses in columns I through AG (Q1-Q25)
- Participant metadata (ID, Email, Name, etc.)
- Likert scale responses (1-7 or text equivalents)

## Output

The generated Excel report includes:
- Individual dimension scores with interpretations
- Key strengths recommendations
- Development areas guidance
- Priority recommendations with icons
- Radar charts showing each participant's profile

## Development

### Project Structure
```
ccip/
├── ccip/                 # Core module
│   ├── __main__.py      # CLI entry point
│   ├── ccip_compose.py  # Report composition
│   ├── ccip_intake.py   # Data processing
│   └── ...
├── app.py               # Streamlit web interface
├── Dockerfile           # Container configuration
└── requirements.txt     # Dependencies
```

### Testing
```bash
pytest tests/
```

## Deployment

Deploy to any Docker-compatible platform:
- Render
- Railway
- Fly.io
- Heroku

The Dockerfile includes all necessary system dependencies for CairoSVG.

## License

[Your License Here]