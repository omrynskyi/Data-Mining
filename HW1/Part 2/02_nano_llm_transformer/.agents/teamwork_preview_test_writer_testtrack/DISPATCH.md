## 2026-09-02T17:24:09Z

You are the E2E Test Suite Lead (teamwork_preview_test_writer).
Your working directory is: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/02_nano_llm_transformer/.agents/teamwork_preview_test_writer_testtrack
Project root: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/02_nano_llm_transformer
Original request: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/02_nano_llm_transformer/.agents/ORIGINAL_REQUEST.md
Project specification: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/02_nano_llm_transformer/PROJECT.md

Instructions:
1. Create your BRIEFING.md and progress.md in your working directory.
2. Read ORIGINAL_REQUEST.md and PROJECT.md carefully.
3. Design and implement the complete E2E testing infrastructure at the project root:
   - Create `TEST_INFRA.md` at project root documenting test philosophy, feature inventory, 4-tier coverage goals, runner invocation, and pass criteria.
   - Implement `test_model.py` per acceptance criteria: initializes model, verifies forward pass tensor shapes, and verifies gradient backpropagation through RoPE, SwiGLU, RMSNorm during a mock SFT backward pass.
   - Implement `test_dashboard.py` per acceptance criteria: launches/tests dashboard via FastAPI TestClient (or httpx), asserts HTTP 200 OK on KV-cache, attention heatmaps, and tokenizer endpoints, and verifies that the CRISP-DM tracker state can be read programmatically with >= 3 stages (Data Preparation, Modeling, Evaluation, etc.).
   - Implement `benchmark_mps.py` per acceptance criteria: runs a text generation task defaulting to `mps` device if available (fallback to cpu), profiles memory usage, and asserts memory does not exceed predefined unified memory limit (4.0 GB).
   - Implement comprehensive 4-tier pytest suites in `tests/`:
     * `tests/conftest.py`: Shared fixtures.
     * `tests/test_tier1_features.py`: Feature coverage (>=5 tests per feature).
     * `tests/test_tier2_boundaries.py`: Boundary and corner cases (>=5 tests per feature).
     * `tests/test_tier3_combinations.py`: Cross-feature pairwise interactions.
     * `tests/test_tier4_workloads.py`: Real-world end-to-end application scenarios.
   - Implement `run_tests.py`: CLI test runner executing all test tiers with detailed reporting and exit code 0 on pass.
   - Publish `TEST_READY.md` at project root summarizing the test suite, test count per tier, runner commands, and feature checklist.
4. Run syntax/import checks on the test infrastructure where possible.
5. Write your handoff.md in your working directory and notify the orchestrator when TEST_READY.md has been created.
