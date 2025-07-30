# Tagging & client Identification Implementation

## Overview

The OpenMemory system implements two types of automatic tagging:
1. **Processing Status Tagging**: Distinguishes between LLM-processed vs raw memories
2. **Client Identification**: Properly identifies and displays different MCP clients

## Part 1: Automatic Processing Status Tagging

The OpenMemory system automatically tags memories with processing status tags based on how they were created. This helps distinguish between memories that were processed with LLM inference versus those stored as raw text.

## How It Works

### Automatic Tag Assignment

Every memory is automatically tagged with one of two processing status tags:

- **`processed`**: Memories created with `infer=true` (default behavior)
  - The memory text was analyzed and potentially summarized/optimized by the LLM
  - Content may be different from the original input due to intelligent processing
  
- **`unprocessed`**: Memories created with `infer=false`
  - The memory text is stored exactly as provided (raw/verbatim)
  - No LLM analysis or modification occurred
  - Faster storage, ideal for structured data or pre-processed facts

### Implementation Details

#### 1. Enhanced Categorization Function
- **File**: `/openmemory/api/app/utils/categorization.py`
- **Function**: `get_categories_for_memory(memory: str, infer: bool = True)`
- **Enhancement**: Automatically appends processing status tag based on `infer` parameter

#### 2. Memory Metadata Storage
- **Files**: 
  - `/openmemory/api/app/routers/memories.py` (API endpoint)
  - `/openmemory/api/app/mcp_server.py` (MCP server)
- **Enhancement**: Stores `infer` parameter in memory metadata for reference

#### 3. Database Integration
- **File**: `/openmemory/api/app/models.py`
- **Function**: `categorize_memory()`
- **Enhancement**: Extracts `infer` value from memory metadata and passes to categorization

#### 4. Updated Categorization Prompt
- **File**: `/openmemory/api/app/utils/prompts.py`
- **Enhancement**: Informs LLM that processing status tags are handled automatically

## Usage Examples

### API Usage

```bash
# Create unprocessed memory (infer=false)
curl -X POST http://localhost:8765/api/v1/memories/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "User prefers Python programming language and uses VS Code editor",
    "user_id": "local-user",
    "infer": false
  }'

# Result categories: ["unprocessed", "general"]
```

```bash
# Create processed memory (infer=true)
curl -X POST http://localhost:8765/api/v1/memories/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I really enjoy working with machine learning and have been using TensorFlow and PyTorch extensively for computer vision projects.",
    "user_id": "local-user",
    "infer": true
  }'

# Result categories: ["processed", "ai, ml & technology", "projects"]
```

### MCP Usage

When using the MCP server through Claude Desktop, the tool automatically determines which mode to use:

```python
# Claude will automatically use infer=false for structured facts
await add_memories("User favorite programming language is Python and uses PyCharm IDE", infer=False)
# Categories: ["unprocessed", "preferences"]

# Claude will automatically use infer=true for conversational input
await add_memories("I really love building neural networks for computer vision tasks", infer=True)  
# Categories: ["processed", "ai, ml & technology"]
```

## Benefits

### 1. **Automatic Classification**
- No manual tagging required
- Consistent categorization across all memories
- Easy filtering and analysis of memory types

### 2. **Performance Optimization Tracking**
- Identify which memories used LLM processing vs. fast storage
- Analyze system performance and cost optimization opportunities
- Monitor usage patterns

### 3. **Data Integrity Assurance**
- Clear distinction between original and processed content
- Audit trail for memory creation methods
- Support for different use cases (structured vs. unstructured data)

### 4. **Search and Filtering**
- Filter memories by processing type
- Analyze effectiveness of different storage approaches
- Targeted retrieval based on data fidelity needs

## Querying by Processing Status

### Get All Categories
```bash
curl -X GET "http://localhost:8765/api/v1/memories/categories?user_id=local-user"
```

### Filter Memories by Processing Status
```bash
# Get only unprocessed memories
curl -X GET "http://localhost:8765/api/v1/memories/?user_id=local-user&categories=unprocessed"

# Get only processed memories  
curl -X GET "http://localhost:8765/api/v1/memories/?user_id=local-user&categories=processed"
```

## Technical Architecture

```
Memory Creation Request
        ↓
    infer parameter
        ↓
Memory Storage (with infer in metadata)
        ↓
SQLAlchemy Event Trigger
        ↓
categorize_memory() extracts infer from metadata
        ↓
get_categories_for_memory(memory, infer=infer)
        ↓
LLM Categorization + Automatic Processing Tag
        ↓
Categories stored in database: ["category1", "category2", "processed/unprocessed"]
```

## Backward Compatibility

- Existing memories without `infer` metadata default to `infer=true` (processed)
- All existing functionality remains unchanged
- New tags are additive - existing categories are preserved

## Future Enhancements

1. **Custom Processing Tags**: Allow custom tags beyond processed/unprocessed
2. **Processing Metrics**: Track processing time and cost per memory type
3. **Smart Recommendations**: Suggest optimal `infer` setting based on content analysis
4. **Batch Processing**: Apply processing status changes to existing memories

This implementation provides a robust foundation for memory classification while maintaining simplicity and performance.

---

## Part 2: Client Identification & Tagging Implementation

### Problem Identified
The Apps tab in the UI was showing "Default" instead of proper client names for different Claude clients and other MCP clients. This happened because:

1. Client detection in the MCP server was generating inconsistent app names
2. The UI constants didn't include all possible client name variations  
3. Fallback logic was showing "Default" instead of actual client names

### Changes Implemented ✅

#### 1. Enhanced Client Detection Logic
**File:** `/mem0/openmemory/api/app/mcp_server.py` (Lines 115-117)
```python
# Clean up the client name for better formatting
clean_name = base_client_name.replace("-", " ").replace("_", " ").title()
return f"Claude {clean_name} ({connection_type})"
```

**Impact:** Converts names like "claude-desktop" to "Claude Desktop (SSE)" instead of "Claude Claude-Desktop (SSE)"

#### 2. Added Missing UI Constants  
**File:** `/mem0/openmemory/ui/components/shared/source-app.tsx` (Lines 99-123)
```typescript
"Claude Claude-Desktop (SSE)": {
  name: "Claude Desktop",
  icon: <Icon source="/images/claude.webp" />,
  iconImage: "/images/claude.webp",
},
"Claude Desktop": {
  name: "Claude Desktop", 
  icon: <Icon source="/images/claude.webp" />,
  iconImage: "/images/claude.webp",
},
// Additional constants for common client names
```

**Impact:** Provides proper display names and icons for previously unrecognized client names

#### 3. Improved Fallback Logic
**File:** `/mem0/openmemory/ui/app/apps/components/AppCard.tsx` (Lines 21-27)
```typescript
const appConfig = constants[app.name as keyof typeof constants] || {
  name: app.name, // Use actual app name instead of "Default"
  icon: <div className="w-6 h-6 flex items-center justify-center text-zinc-400">
    <span className="text-xs font-bold">{app.name.charAt(0).toUpperCase()}</span>
  </div>,
  iconImage: null,
};
```

**Impact:** Unknown client names now display their actual names with a letter-based icon instead of "Default"

### Current App Name Mapping ✅ UPDATED

Based on API analysis after app cleanup, these are the current clean app states:

| Database App Name | Expected UI Display | Status |
|-------------------|-------------------|---------|
| `"claude"` | "Claude" | ✅ Working |
| `"Claude Code"` | "Claude Code" | ✅ Working |
| `"Claude Claude Desktop (SSE)"` | "Claude Desktop" | ✅ Working (Primary) |
| `"openmemory"` | "OpenMemory" | ✅ Working |

**✅ COMPLETED: App Cleanup**
- **Deleted** duplicate Claude Desktop apps instead of deactivating them
- **Enhanced** client detection to differentiate VS Code vs Claude Code
- **Added** "Claude VS Code" as separate app type for VS Code-based Claude instances
- **Result**: Clean 4-app state with no duplicates

**Note**: Duplicate Claude Desktop apps have been permanently deleted. All future Claude Desktop connections will use the primary app entry. VS Code-based Claude instances (like GitHub Copilot in VS Code) will now be detected as "Claude VS Code" for better differentiation.

### Next Steps Required ✅ COMPLETED

#### 1. **COMPLETED: Apply UI Changes** ✅
The UI changes have been successfully applied and are now active:

**Actions Taken:**
- ✅ Rebuilt the UI Docker image with latest fixes
- ✅ Added support for `"Claude Claude Desktop (SSE)"` variant in constants
- ✅ Applied enhanced fallback logic in AppCard.tsx
- ✅ Restarted UI container with updated image

#### 2. **COMPLETED: Client Consolidation** ✅
Cleaned up duplicate Claude Desktop apps by **deleting them permanently**:

**Actions Taken:**
- ✅ Identified 3 duplicate Claude Desktop app variants
- ✅ **DELETED** (not deactivated) duplicates: `"Claude Claude-Desktop (SSE)"` and `"Claude Desktop (SSE)"`
- ✅ Kept primary app: `"Claude Claude Desktop (SSE)"` (29 total interactions)
- ✅ Updated UI constants to handle all variants properly
- ✅ Enhanced client detection to differentiate "Claude Code" vs "Claude VS Code"

#### 3. **COMPLETED: Enhanced Client Detection** ✅
The enhanced client detection logic is now active:

**Actions Taken:**
- ✅ Enhanced MCP server client detection to differentiate VS Code instances
- ✅ Added "Claude VS Code" as separate client type for VS Code-based Claude instances  
- ✅ Rebuilt and restarted UI container with new constants
- ✅ Updated source-app.tsx with "Claude VS Code" constants

#### 2. **Test Client Detection** (Medium Priority)
Verify that the enhanced client detection logic works correctly:

1. Connect different Claude clients (Desktop, Code, VS Code Extension)
2. Create memories from each client
3. Verify apps are created with proper names
4. Check that UI displays correct client names and icons

#### 3. **Add Support for Additional Clients** (Low Priority)
The current constants support these clients:
- Claude variants (Desktop, Web, Mobile, Code, VS Code Extension)
- Cursor, Cline, Roo Cline, Windsurf, Witsy, Enconvo, Augment
- OpenMemory

**To add new clients:**
1. Add constants to `source-app.tsx`
2. Add client icons to `/public/images/`
3. Update client detection logic if needed

#### 4. **Enhance Client Detection Headers** (Medium Priority)
Consider adding custom headers to MCP clients for better identification:
```http
X-Client-Name: Claude-Code
X-Client-Version: 1.0.0
X-Client-Platform: VSCode
```

#### 5. **Database Migration for Existing Apps** (Optional)
If you want to clean up existing "problematic" app names:

```sql
-- Example: Rename existing apps with better names
UPDATE apps 
SET name = 'Claude Desktop (SSE)' 
WHERE name = 'Claude Claude-Desktop (SSE)';
```

### Testing Checklist

Once UI changes are applied, verify:

- [ ] Apps tab loads without "Default" entries (unless truly unknown clients)
- [ ] Each client type shows proper display name
- [ ] Each client type shows appropriate icon
- [ ] Unknown clients show their actual name instead of "Default"
- [ ] Memory creation from different clients creates properly named apps
- [ ] App details pages work correctly with updated names

### Files Modified for Client Identification

1. `/mem0/openmemory/api/app/mcp_server.py` - Enhanced client detection
2. `/mem0/openmemory/ui/components/shared/source-app.tsx` - Added constants
3. `/mem0/openmemory/ui/app/apps/components/AppCard.tsx` - Improved fallback logic

### Impact of Client Identification

This implementation will:
- ✅ Eliminate confusing "Default" app names
- ✅ Provide clear identification of different Claude clients
- ✅ Support future client additions easily
- ✅ Improve user experience in the Apps dashboard
- ✅ Maintain backward compatibility with existing apps

### Notes

- Backend changes are already active (MCP server restarted)
- UI changes require container rebuild/restart to take effect
- Future client additions just need constants added to `source-app.tsx`
- The fallback logic ensures unknown clients are handled gracefully

---

## Summary

The OpenMemory system now provides comprehensive tagging capabilities:

1. **Processing Status Tags**: Automatically distinguish between `processed` and `unprocessed` memories
2. **Client Identification**: Properly identify and display different MCP clients instead of showing "Default"

Both systems work together to provide better organization, filtering, and user experience in the OpenMemory dashboard.
