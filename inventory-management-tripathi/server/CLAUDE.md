# CLAUDE.md - Server

This file provides guidance to Claude Code (claude.ai/code) when working with the FastAPI backend.

## Running the Server

```bash
# From server directory
uv run python main.py
# Server runs on http://localhost:8001
# API docs at http://localhost:8001/docs
```

## Development Best Practices

### API Design Principles

**RESTful Design:**
- Use appropriate HTTP methods (GET for retrieval, POST for creation, etc.)
- Return proper status codes (200, 201, 404, 400, 500)
- Use plural nouns for resource endpoints (`/api/orders`, not `/api/order`)
- Keep URLs simple and predictable

**Request/Response:**
- Always validate input with Pydantic models
- Return consistent response structure
- Include error details in error responses
- Use ISO 8601 for dates (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)

### Adding New Endpoints

**Process:**
1. Define Pydantic model for data validation
2. Create endpoint function with clear name
3. Add route decorator with explicit path
4. Implement business logic
5. Handle errors appropriately
6. Write tests in `tests/backend/`

**Example Pattern:**
```python
class MyModel(BaseModel):
    id: str
    name: str
    value: float

@app.get("/api/resource", response_model=List[MyModel])
def get_resources(
    filter_param: Optional[str] = None,
    category: Optional[str] = None
):
    """Get resources with optional filtering."""
    results = all_resources

    if filter_param and filter_param != 'all':
        results = [r for r in results if r['field'] == filter_param]

    if category and category != 'all':
        results = [r for r in results if r['category'].lower() == category.lower()]

    return results
```

### Data Model Best Practices

**Pydantic Models:**
- Define once, use everywhere
- Make optional fields explicitly `Optional[Type]`
- Use descriptive field names
- Add default values where appropriate
- Keep models close to their usage

**Model Updates:**
- When adding fields to JSON data, update Pydantic models
- When removing fields, mark as Optional first, then remove
- Consider backwards compatibility
- Update tests when models change

### Filtering Best Practices

**Standard Pattern:**
- Accept filter parameters as optional query params
- Check for 'all' value and skip that filter
- Use lowercase comparison for case-insensitive matching
- Apply filters sequentially for code clarity
- Don't mutate original data - filter on copies

**Filter Implementation:**
```python
def filter_data(data, warehouse=None, category=None):
    """Filter data by multiple criteria."""
    filtered = data

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered
                   if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered
                   if item.get('category', '').lower() == category.lower()]

    return filtered
```

**Date/Time Filtering:**
- Support both direct month match (2025-01) and quarters (Q1-2025)
- Parse date strings safely
- Handle missing/null dates gracefully
- Consider timezone if adding real database

### Error Handling

**Use HTTPException:**
```python
from fastapi import HTTPException

@app.get("/api/item/{item_id}")
def get_item(item_id: str):
    item = find_item(item_id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"Item {item_id} not found"
        )
    return item
```

**Best Practices:**
- Return 404 for "not found" errors
- Return 400 for bad input/validation errors
- Return 500 for server errors (let FastAPI handle these)
- Include helpful error messages
- Log errors for debugging

### Mock Data Management

**Pattern:**
- Load all data from JSON files at startup
- Data lives in memory during server runtime
- Changes don't persist (restart reloads from files)
- Keep JSON files well-formatted and validated

**Adding New Data:**
1. Update JSON file in `server/data/`
2. Update Pydantic model if structure changed
3. Restart server to reload data
4. Verify with API docs (/docs endpoint)

**Data Consistency:**
- Ensure SKUs in orders reference valid inventory items
- Keep category names consistent across data files
- Use same date format everywhere
- Validate JSON structure before committing

### CORS Configuration

**Development:**
- Allow all origins during development (`allow_origins=["*"]`)
- Useful for frontend dev server on different port

**Production:**
- Restrict to specific origins only
- Example: `allow_origins=["https://yourdomain.com"]`
- Never use wildcard (*) in production
- Configure based on deployment environment

### Testing API Endpoints

**Using FastAPI Docs:**
1. Start server
2. Navigate to http://localhost:8001/docs
3. Click endpoint to expand
4. Click "Try it out"
5. Fill in parameters
6. Execute and verify response

**Using pytest:**
```python
def test_endpoint(client):
    response = client.get("/api/endpoint?param=value")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
```

**What to Test:**
- Successful requests return 200
- Invalid IDs return 404
- Filters work correctly
- Response structure matches model
- Calculations are accurate
- Edge cases (empty results, invalid input)

### Performance Considerations

**In-Memory Data:**
- Fast reads (no database queries)
- No indexing needed for demo
- All filtering happens in Python
- Reasonable for small datasets (<10K items)

**If Scaling:**
- Add database (PostgreSQL, MongoDB)
- Implement pagination
- Add caching layer (Redis)
- Use database indexes for common filters
- Consider async database queries

### Code Organization

**When to Extract:**
- Filtering logic used in multiple endpoints → Extract to utility function
- Complex business logic → Move to separate module
- Data validation beyond Pydantic → Create custom validators
- Repeated calculations → Extract to helper functions

**Module Structure for Growth:**
```
server/
├── main.py           # API endpoints only
├── models.py         # Pydantic models
├── services/         # Business logic
│   ├── inventory.py
│   └── orders.py
├── utils/            # Helper functions
│   └── filters.py
└── data/             # JSON data files
```

### Common Pitfalls

**Avoid:**
- ❌ Mutating global data (filter on copies)
- ❌ Missing Pydantic model updates when JSON changes
- ❌ Inconsistent filter parameter names across endpoints
- ❌ Returning raw dict instead of Pydantic model
- ❌ Not handling None/null values in data

**Do:**
- ✅ Validate all input with Pydantic
- ✅ Return typed responses (response_model)
- ✅ Handle optional parameters gracefully
- ✅ Keep endpoints focused and simple
- ✅ Write tests for new endpoints

### Debugging

**Techniques:**
- Use FastAPI's automatic docs for quick testing
- Print statements in endpoint functions (shows in terminal)
- Check Pydantic validation errors in response
- Use Python debugger (`import pdb; pdb.set_trace()`)
- Review JSON data files for structure issues

**Common Issues:**
- Data not loading → Check JSON file path
- Validation errors → Verify Pydantic model matches data
- Empty results → Check filter logic and data
- 404 errors → Verify route path and HTTP method

### Security Notes

**For Production:**
- Add authentication/authorization
- Validate and sanitize all input
- Use HTTPS only
- Implement rate limiting
- Add input size limits
- Use environment variables for sensitive config
- Never commit secrets to git

**Current State:**
- No authentication (demo only)
- CORS allows all origins
- No rate limiting
- No input validation beyond types
- Suitable for local development only

## Quick Reference

**Start server:** `uv run python main.py`
**API docs:** http://localhost:8001/docs
**Run tests:** `cd ../tests && uv run pytest backend/ -v`
**Add endpoint:** Define model → Add route → Write tests
**Add filter:** Add query param → Check 'all' value → Filter data
