# Optimize Codebase

Perform a comprehensive codebase optimization:

1. **Scan the entire codebase** to identify:
   - Unused functions, variables, and imports
   - Dead code and unreachable code paths
   - Unused dependencies in package.json and pyproject.toml
   - Duplicate code that can be refactored
   - Unused CSS classes and styles

2. **Analyze code quality**:
   - Look for performance bottlenecks
   - Identify inefficient patterns (e.g., unnecessary re-renders, inefficient loops)
   - Check for missing error handling
   - Find hardcoded values that should be constants

3. **Remove unused code**:
   - Delete unused imports and functions
   - Remove commented-out code
   - Clean up unused dependencies
   - Remove unused CSS/styles

4. **Optimize existing code**:
   - Simplify complex logic
   - Extract repeated code into reusable functions
   - Optimize database queries or API calls
   - Improve algorithm efficiency where applicable

5. **Provide a summary** of:
   - What was removed (with file locations)
   - What was optimized (with before/after explanations)
   - Recommendations for further improvements
   - Any breaking changes or things to test

Focus on both frontend (Vue/JavaScript) and backend (Python/FastAPI) code. Be thorough but conservative - only remove code you're confident is unused.
