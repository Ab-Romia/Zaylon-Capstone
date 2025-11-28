# Agent Evaluation Guide

This evaluation suite tests the Flowinit agent system against a golden dataset of 30 realistic customer interactions.

---

## Quick Start

### Using OpenAI as Judge (Default)

```bash
export OPENAI_API_KEY='your-openai-key-here'
cd tests/evaluation
python run_eval.py
```

### Using Gemini as Judge (Cheaper!)

```bash
export GEMINI_API_KEY='your-gemini-key-here'
export JUDGE_PROVIDER=gemini
cd tests/evaluation
python run_eval.py
```

---

## LLM Judge Provider Options

The evaluation script supports **both OpenAI and Gemini** as judge models.

### Option 1: OpenAI (Default)

**Model**: GPT-4o

**Cost**: ~$0.15 per evaluation run (30 test cases)

**Setup**:
```bash
export OPENAI_API_KEY='sk-your-key-here'
# JUDGE_PROVIDER defaults to "openai"
```

**Pros**:
- Slightly more consistent scoring
- Default option, no extra config

**Cons**:
- More expensive
- Requires OpenAI account

### Option 2: Gemini (Cost-Effective!)

**Model**: Gemini 1.5 Pro

**Cost**: ~$0.05 per evaluation run (30 test cases) - **70% cheaper!**

**Setup**:
```bash
export GEMINI_API_KEY='your-gemini-key-here'
export JUDGE_PROVIDER=gemini
```

**Pros**:
- **70% cheaper** than OpenAI
- FREE tier available (60 requests/min)
- Very similar scoring quality

**Cons**:
- Slightly less consistent than GPT-4o
- Requires Google account

---

## Cost Comparison

**For 1 evaluation run (30 test cases):**

| Provider | Model | Input Tokens | Output Tokens | Cost per Run | Cost for 10 Runs |
|----------|-------|--------------|---------------|--------------|------------------|
| OpenAI | GPT-4o | ~20K | ~5K | **$0.15** | **$1.50** |
| Gemini | 1.5 Pro | ~20K | ~5K | **$0.05** | **$0.50** |

**Savings with Gemini: 70%!**

For frequent evaluation (e.g., during development), using Gemini can save significant costs.

---

## Running Evaluations

### Prerequisites

1. **Start the API server**:
   ```bash
   python main.py
   ```
   Server should be running on `http://localhost:8000`

2. **Set API key for judge**:
   ```bash
   # For OpenAI (default)
   export OPENAI_API_KEY='your-key'

   # OR for Gemini (cheaper)
   export GEMINI_API_KEY='your-key'
   export JUDGE_PROVIDER=gemini
   ```

### Run Evaluation

```bash
cd tests/evaluation
python run_eval.py
```

### Expected Output

```
================================================================================
FLOWINIT AGENT EVALUATION SUITE
================================================================================
Started: 2025-11-27 20:00:00
API Base URL: http://localhost:8000
Judge Provider: GEMINI
Judge Model: gemini-1.5-pro
================================================================================

✓ Loaded 30 test cases from golden dataset

================================================================================
Test 1: I want to buy a red hoodie in size L
Expected: sales agent | Easy | English
================================================================================
✓ Agent: sales
✓ Tools: ['search_products_tool']
✓ Response: It seems that we currently have...
✓ Time: 14578ms
  Evaluating with LLM judge...
  Intent: 1.00 | Tool: 1.00 | Quality: 0.90 | Overall: 0.90
  Reasoning: The agent correctly identified...

...

================================================================================
EVALUATION SUMMARY
================================================================================
Total Tests: 30
Successful API Calls: 30 (100.0%)

Average Scores:
  Intent Accuracy:    88.3%
  Tool Selection:     73.3%
  Response Quality:   80.3%
  Overall Success:    69.2%

Performance:
  Avg Execution Time: 8367ms
  Tests with ≥80% Success: 46.7%

✓ PASS! Agent achieved 69.2% overall success rate.
================================================================================
```

---

## Output Files

After running, you'll get:

1. **`results.csv`** - Detailed results for each test case
   - All scores, tool calls, responses
   - Use for deep analysis

2. **`../../EVALUATION_REPORT.md`** - Markdown report
   - Executive summary
   - Performance by difficulty/language/agent
   - Top performing and struggling scenarios
   - Recommendations

---

## Evaluation Criteria

Each test is scored 0-1 on four dimensions:

### 1. Intent Accuracy
- Did the agent route to the correct specialist (sales/support)?
- **Expected**: 90%+ for production

### 2. Tool Selection
- Did the agent call appropriate tools?
- For product queries: search_products_tool
- For FAQs: search_knowledge_base_tool
- For orders: check_order_status_tool or get_order_history_tool
- **Expected**: 85%+ for production

### 3. Response Quality
- Is the response helpful and polite?
- Correct language (Arabic/Franco-Arabic/English)?
- Addresses customer's question?
- **Expected**: 90%+ for production

### 4. Overall Success
- Would this satisfy a real customer?
- Combines all criteria
- **Target**: 80%+ for production

---

## Troubleshooting

### "API returned 401"
- Check that API_KEY in .env matches the one used in the test
- Default test key: `Xg-XWT6bR1ZdssyX6kZ9jI2DbrX__EZRgYeTvTFIkjY`

### "OPENAI_API_KEY not set"
- Set the environment variable: `export OPENAI_API_KEY='your-key'`
- Or switch to Gemini: `export JUDGE_PROVIDER=gemini`

### "Connection refused"
- Make sure server is running: `python main.py`
- Check server is on port 8000: `curl http://localhost:8000/health`

### "Judge error: rate limit"
- **OpenAI**: Wait a minute and retry
- **Gemini**: Free tier is 60 requests/min - should be fine for 30 tests
- Add delays between tests if needed

---

## Golden Dataset

The evaluation uses 30 hand-crafted test cases covering:

**By Difficulty:**
- 6 Easy: Basic product searches, simple FAQs
- 15 Medium: Standard queries, order tracking
- 9 Hard: Mixed intent, memory retrieval, edge cases

**By Language:**
- English: Product searches, support queries
- Arabic: Native Egyptian queries
- Franco-Arabic: "3rabizi" style messages

**By Intent:**
- Product searches
- Purchases
- Order tracking
- FAQs (returns, shipping, payment)
- Complaints
- Mixed scenarios

---

## Customizing Evaluation

### Change API Base URL

```bash
export API_BASE_URL='https://your-production-url.com'
python run_eval.py
```

### Use Different Judge Model

Edit `run_eval.py`:
```python
# For Gemini Flash (faster, cheaper)
judge_model = "gemini-1.5-flash"

# For GPT-4o-mini (cheaper OpenAI)
judge_model = "gpt-4o-mini"
```

### Add New Test Cases

Edit `golden_dataset.csv` and add rows with:
- test_id
- input_message
- expected_intent
- expected_agent
- expected_tool
- difficulty (Easy/Medium/Hard)
- language (English/Arabic/Franco-Arabic)
- notes

---

## Tips for Best Results

1. **Warm up the server**: Run 1-2 test queries before evaluation
2. **Use Gemini for iteration**: Save money during development
3. **Use OpenAI for final**: Slightly more consistent for prod validation
4. **Run multiple times**: Average scores across 3 runs for stability
5. **Check individual failures**: Read `results.csv` for failing tests

---

## Next Steps

1. **Review results**: Check `EVALUATION_REPORT.md`
2. **Fix failures**: Focus on 0% success tests first
3. **Iterate**: Improve prompts, add FAQs, fix routing
4. **Re-evaluate**: Run again to measure improvement
5. **Deploy**: Once 80%+ success rate is achieved

---

**Questions?** See the main project README or open an issue.
