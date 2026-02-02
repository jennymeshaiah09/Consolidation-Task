# Product Data Consolidation Tool

A modern multi-phase Streamlit application for consolidating monthly product data, enriching it with LLM-generated keywords, and analyzing peak popularity trends.

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Google Gemini API key (for keyword generation)

### Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your API key:
   - Create a `.env` file in the project root
   - Add your Google Gemini API key:
     ```
     GOOGLE_API_KEY=your_api_key_here
     ```
   - Get your key from: https://aistudio.google.com/app/apikey

### Running the Application

#### New Multi-Page App (Recommended)
```bash
streamlit run Home.py
```

#### Legacy Single-Page App
```bash
streamlit run app.py
```

## 📁 Project Structure

```
Consolidation Task/
├── Home.py                          # Main entry point (multi-page app)
├── pages/                           # Multi-page navigation
│   ├── 1_📊_Data_Consolidation.py  # Phase 1: Data upload & consolidation
│   ├── 2_🔤_Keywords_Categories.py  # Phase 2: Keyword generation
│   ├── 3_📈_MSV_Management.py       # Phase 3: MSV placeholder (Tenny)
│   ├── 4_⭐_Peak_Analysis.py        # Phase 4: Peak popularity analysis
│   └── 5_💡_Insights.py             # Phase 5: Future analytics
├── utils/                           # Shared utilities
│   ├── ui_components.py             # Modern UI components & CSS
│   └── state_manager.py             # Session state management
├── src/                             # Core business logic
│   ├── ingestion.py                 # File loading & parsing
│   ├── validation.py                # Data validation
│   ├── normalization.py             # Product categorization
│   ├── consolidation.py             # Data consolidation pipeline
│   └── llm_keywords.py              # LLM keyword generation
├── app.py                           # Legacy single-page app
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variable template
└── PLAN.md                          # Detailed project documentation
```

## 🎯 Features

### Phase 1: Data Consolidation
- Upload ZIP files containing monthly product data (Jan-Dec 2025)
- Automatic file format detection (CSV/Excel)
- Encoding handling (UTF-16, UTF-8, Latin-1)
- Column validation and normalization
- Unified product consolidation

### Phase 2: Keywords & Categories
- LLM-powered keyword generation using Google Gemini
- Batch processing (20 products per API call)
- Automatic product categorization
  - **BWS**: Beers, Wines, Spirits, Cider, Rum
  - **Pets**: Accessories, Clothing, Food, Supplements
  - **Electronics**: Accessories, TV, Laptop, Kitchen appliances
- Trial mode for testing

### Phase 3: MSV Management
- Placeholder for Monthly Search Volume data
- Managed by teammate Tenny
- 36 date columns (Jan 2023 - Dec 2025)

### Phase 4: Peak Analysis
- Variance-based peak popularity calculation
- Top 4 month analysis
- Interactive filtering by peak months
- Visual distribution charts
- Export peak analysis results

### Phase 5: Insights & Analytics (Coming Soon)
- Advanced trend analysis
- Seasonal pattern detection
- Keyword intelligence
- Custom dashboards

## 📊 Input Requirements

### ZIP File Contents
- Monthly files for Jan-Dec 2025
- Supported formats: CSV, Excel (.xlsx)
- Filename formats:
  - `Mon-2025.xlsx` (e.g., `Jan-2025.xlsx`)
  - `Mon 2025.csv` (e.g., `Apr 2025.csv`)
  - `Prefix Mon 2025.csv` (e.g., `BWS Apr 2025.csv`)

### Required Columns
Each monthly file must contain:
- **Product Title** (or "Title")
- **Brand**
- **Availability**
- **Price range max.**
- **Popularity rank**

**Note**: December file is mandatory

## 🎨 UI/UX Features

### Modern Design
- Green/Teal color scheme (Fresh & Data-Focused)
- Card-based layouts with shadows and hover effects
- Gradient headers
- Responsive grid layouts
- Progress tracking across phases

### Navigation
- Multi-page architecture with automatic sidebar navigation
- Breadcrumb navigation
- Phase status indicators
- Quick stats dashboard on homepage

### Session State
- Data persists across page navigation
- Phase completion tracking
- Real-time progress updates

## 🔧 Configuration

### Environment Variables
- `GOOGLE_API_KEY` - Required for keyword generation

### Customization
- Batch size: Adjust in `src/llm_keywords.py` (default: 20)
- Model: Change `model_name` parameter (default: gemma-3-4b-it)
- Safety settings: Configured in `src/llm_keywords.py`

## 📝 Output

### Consolidated Excel File
The final output includes:
- Product Title
- Product Max Price (from December)
- Product Category (auto-classified)
- Product Keyword (LLM-generated)
- Product Brand
- Availability (from December)
- Monthly Popularity (Jan-Dec columns)
- MSV Date Columns (36 columns, Jan 2023 - Dec 2025)
- Peak Seasonality (placeholder)
- Peak Popularity (calculated)

## 🐛 Troubleshooting

### Common Issues

1. **API Key Error**
   - Ensure `.env` file exists in project root
   - Verify `GOOGLE_API_KEY` is set correctly
   - Test API connection in Phase 2

2. **File Upload Errors**
   - Check file encoding (UTF-16 supported)
   - Verify December file is included
   - Ensure all required columns are present

3. **Import Errors**
   - Install all dependencies: `pip install -r requirements.txt`
   - Check Python version (3.8+)

4. **Session State Lost**
   - Don't refresh the browser page
   - Use navigation buttons instead of browser back/forward

## 📚 Additional Resources

- [Detailed Project Plan](PLAN.md)
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [Streamlit Documentation](https://docs.streamlit.io)

## 🤝 Contributing

### Team Members
- **Phase 1-2, 4**: Implementation complete
- **Phase 3**: Tenny (MSV data management)
- **Phase 5**: Future development

### Feedback
Use the feedback form in Phase 5 to suggest new features or improvements.

## 📄 License

This project is part of an internal product data consolidation workflow.

## 📞 Support

For questions or issues:
1. Check the [PLAN.md](PLAN.md) documentation
2. Review the error messages in the UI
3. Contact the development team

---

**Version**: 2.0 (Multi-Page Architecture)
**Last Updated**: 2026-01-31
