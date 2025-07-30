# MCP Testing Instructions for Claude Desktop

## How to Test the infer Parameter Through Claude Desktop

Since the MCP server is running and configured, you can test both `infer=true` and `infer=false` directly in Claude Desktop.

### Test 1: infer=false (Raw Storage)
**In Claude Desktop, try saying:**

"Please remember this exact information using infer=false: CLAUDE TEST: User specializes in machine learning and prefers PyTorch over TensorFlow for deep learning projects."

**Expected behavior:**
- Claude should use the `add_memories` tool with `infer=false`
- The text should be stored exactly as provided
- Response should show the exact text was preserved

### Test 2: infer=true (Intelligent Processing) 
**In Claude Desktop, try saying:**

"Please remember that I really enjoy building web applications using modern JavaScript frameworks. I spend most of my time working with React and Next.js, and I love how TypeScript helps catch errors early in development. I also use Tailwind CSS for styling because it's so efficient."

**Expected behavior:**
- Claude should use the `add_memories` tool with `infer=true` (default)
- The LLM should process and summarize the text
- Response should show a condensed, intelligent version

### Test 3: Search Memories
**In Claude Desktop, try saying:**

"What do you remember about my programming preferences?"

**Expected behavior:**
- Claude should use the `search_memory` tool
- Should return both the raw stored memory and the processed memory
- You should see both types of memories in the results

## Verification

After running these tests, you can verify the results by:

1. **Checking the database via API:**
```bash
curl "http://localhost:8765/api/v1/memories/filter" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "local-user"}'
```

2. **Looking at the MCP server logs:**
```bash
docker-compose logs openmemory-mcp --tail=20
```

## Expected Results

You should see:
- **Raw memory**: "CLAUDE TEST: User specializes in machine learning and prefers PyTorch over TensorFlow for deep learning projects."
- **Processed memory**: Something like "Enjoys web development with React, Next.js, TypeScript, and Tailwind CSS"

This confirms that the MCP server correctly handles both storage modes through Claude Desktop's MCP integration.
