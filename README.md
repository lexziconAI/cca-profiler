# CCA Profiler

**CCA Profiler** is an evidence-based reflection tool designed to help participants identify and adapt their communication tendencies in diverse and multicultural workplaces.

This report benchmarks your ability to recognise, respect, and adapt to cultural differences so you can communicate and work effectively across diverse settings. It does not mean being an expert in every culture.

CCA emphasises staying consciously aware of your cultural surroundings, noticing the clues and cues in people's behaviours, communication styles, and expectations, and making informed judgments based on observations and facts rather than assumptions. At its core, CCA requires placing the interests, feelings, and cultural context of others alongside your own, recognising that what feels natural or "professional" in one culture may not be the same in another.

While not a psychometric assessment, the CCA Profiler draws on established, research-backed frameworks in organisational psychology, intercultural communication, and leadership studies.

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
docker build -t cca-profiler .
docker run -p 8501:8501 cca-profiler
```

Then open http://localhost:8501 in your browser.

## Configuration

- `OPENAI_API_KEY` must be set as a Render environment variable (already done).
- `APP_PASSWORD` (optional) protects the app; when set, a password prompt appears.

## Usage

### Command Line
```bash
python -m ccip --input survey_data.xlsx --output results.xlsx
```

### Web Interface
1. Upload your survey Excel/CSV file
2. Click "Process Survey Data"
3. Download the generated CCA Profiler report

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

## Scale & Inputs

This tool strictly uses a **5-point Likert** scale. Inputs may be numeric (1..5) or text:
- Strongly Disagree=1, Disagree=2, Neutral/Neither Agree nor Disagree=3, Agree=4, Strongly Agree=5.

Any 6/7 responses or phrases like "somewhat agree/disagree" are rejected.
Values are averaged per dimension and then mapped from **1..5 → 0..5** for reporting (radar, banding, summaries).

## License

[Your License Here]