# MCP Tool Usage Antipatterns - Lessons Learned

**Date:** 2025-11-17
**Context:** Critical failures in tool usage that wasted time and caused confusion

---

## 🚨 Antipattern 1: Calling Tools Without Required Parameters

### What Happened

**Error:**
```
Error calling tool: Tool call arguments for mcp were invalid.
```

**Root Cause:**
- Called `write_note()` with **zero parameters**
- Tool definition clearly shows `title`, `content`, `folder` are **REQUIRED**
- Failed to read tool definition before calling

### The Tool Definition (Was Available All Along)

```python
mcp_advanced-memory-mcp_write_note
    title: The title of the note (REQUIRED)
    content: Markdown content for the note (REQUIRED)
    folder: Folder path relative to project root (REQUIRED)
    tags: Optional tags
    entity_type: Optional, defaults to "note"
    project: Optional project name
```

### Why This Happened

1. **Assumed tool would work without parameters** (mind-reading assumption)
2. **Didn't check tool definition** before calling
3. **No validation** of required parameters before tool call
4. **Pattern**: Jumping to tool call without reading schema

### How to Avoid This

#### ✅ **MANDATORY CHECKLIST Before Any Tool Call:**

1. **Read tool definition first**
   - Check function signature in available tools
   - Identify REQUIRED vs OPTIONAL parameters
   - Note parameter types and formats

2. **Validate parameters exist**
   - List all required parameters
   - Ensure all required params have values
   - Check parameter formats match requirements

3. **Use explicit parameter names**
   ```python
   # ❌ BAD: Positional, unclear
   write_note("Title", "Content", "folder")

   # ✅ GOOD: Named parameters, clear
   write_note(
       title="Title",
       content="Content",
       folder="folder"
   )
   ```

4. **Test with minimal valid call first**
   - Start with only required parameters
   - Add optional parameters incrementally
   - Verify each parameter works

#### 🔧 **Systematic Approach:**

```python
# STEP 1: Read tool definition
# Tool: mcp_advanced-memory-mcp_write_note
# Required: title (str), content (str), folder (str)
# Optional: tags, entity_type, project

# STEP 2: Prepare parameters
title = "My Note Title"
content = "# My Note\n\nContent here..."
folder = "development"

# STEP 3: Validate (mental check)
assert title, "title is required"
assert content, "content is required"
assert folder, "folder is required"

# STEP 4: Call with named parameters
result = write_note(
    title=title,
    content=content,
    folder=folder
)
```

---

## 🚨 Antipattern 2: Using `recent_activity` for Newly Created Notes

### What Happened

**Expectation:**
- Create note with `write_note()`
- Immediately call `recent_activity(timeframe="1m")`
- Expect to find the newly created note

**Reality:**
- `recent_activity` returned **0 results**
- Note was successfully created (got permalink)
- Note was **immediately findable** via `adn_search()`
- Note was **immediately readable** via permalink

### Root Cause

**`recent_activity` has indexing delay:**
- Uses database queries that may not be immediately updated
- Indexing happens asynchronously
- Time-based queries may miss notes created seconds ago
- Designed for finding **older** notes, not **newly created** ones

### The Correct Pattern

#### ❌ **WRONG: Using recent_activity for new notes**
```python
# Create note
result = write_note(title="Test", content="...", folder="dev")
# Get permalink from result: "dev/test"

# Try to find it immediately
recent = recent_activity(timeframe="1m")  # ❌ Returns 0 results!
```

#### ✅ **CORRECT: Use search or permalink for new notes**
```python
# Create note
result = write_note(title="Test", content="...", folder="dev")
# Get permalink from result: "dev/test"

# Option 1: Use permalink directly (IMMEDIATE)
note = read_note(identifier="dev/test")  # ✅ Works immediately!

# Option 2: Use search with keywords (IMMEDIATE)
results = adn_search(query="test", operation="notes")  # ✅ Works immediately!

# Option 3: Use recent_activity for OLDER notes (NOT immediate)
recent = recent_activity(timeframe="7d")  # ✅ Works for notes from days ago
```

### When to Use Each Method

| Method | Use Case | Timing | Reliability |
|--------|----------|--------|-------------|
| **Permalink** | Just created note | Immediate | ✅ 100% |
| **adn_search** | Find by keywords | Immediate | ✅ 100% |
| **recent_activity** | Find older notes | Delayed (indexing) | ⚠️ May miss new notes |

### How to Avoid This

1. **For newly created notes:**
   - ✅ Use **permalink** from creation response
   - ✅ Use **adn_search** with keywords
   - ❌ **Don't** use `recent_activity` immediately

2. **For older notes:**
   - ✅ Use `recent_activity` with appropriate timeframe
   - ✅ Use `adn_search` with date filters
   - ✅ Use `adn_navigation` with time-based queries

3. **Pattern recognition:**
   - If note was created < 1 minute ago → use permalink or search
   - If note was created > 1 hour ago → `recent_activity` should work
   - If unsure → use search (always works)

---

## 📋 **Pre-Flight Checklist for Tool Calls**

Before calling ANY MCP tool:

- [ ] **Read tool definition** - Check required/optional parameters
- [ ] **List all required parameters** - Ensure all have values
- [ ] **Validate parameter formats** - Types, constraints, examples
- [ ] **Use named parameters** - Don't rely on positional args
- [ ] **Check return value** - Understand what you'll get back
- [ ] **Plan error handling** - What if it fails?
- [ ] **Consider alternatives** - Is this the right tool for the job?

### For Note Operations Specifically:

- [ ] **Newly created note?** → Use permalink or search, NOT recent_activity
- [ ] **Older note?** → recent_activity or search with date filters
- [ ] **Have permalink?** → Use it directly (fastest, most reliable)
- [ ] **Searching?** → Use specific keywords, not generic terms

---

## 🎯 **Key Takeaways**

1. **Always read tool definitions** before calling
2. **Never assume** tools work without required parameters
3. **Use named parameters** for clarity and safety
4. **Understand tool limitations** (e.g., indexing delays)
5. **Choose the right tool** for the job (search vs recent_activity)
6. **Test incrementally** - start simple, add complexity

---

## 🔗 **Related Documentation**

- [MCP Tool Documentation Standards](mcp-tool-documentation-standards.md)
- [Bulletproof MCP Guide](BULLETPROOF_MCP_GUIDE.md)
- [FastMCP Best Practices](../fastmcp-best-practices.md)

---

**Status:** ✅ Documented
**Last Updated:** 2025-11-17
**Lessons Learned:** Always read tool definitions, understand tool limitations, use appropriate methods for the task
