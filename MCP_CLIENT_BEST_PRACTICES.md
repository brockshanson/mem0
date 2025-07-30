# 🎯 OpenMemory MCP Client Best Practices

## Overview

Based on research of the enhanced OpenMemory MCP server configuration and analysis of well-structured ChatGPT memory patterns, this guide provides best practices for external clients using the MCP server tools.

## 🔧 Available MCP Tools

```python
# Primary tools available to external clients:
add_memories(text: str, infer: bool = True, async_mode: bool = False) -> str
search_memory(query: str) -> str  
list_memories() -> str
delete_all_memories() -> str
```

## 📊 Data Structure Strategies

### **✅ Structured Facts (infer=false)**

**When to use:** Clear, factual statements that don't need LLM processing

**Format patterns:**
```python
# Professional Information
add_memories("Works as Solutions Engineer at Summit Technology, an MSP in Salt Lake City, Utah", infer=False)
add_memories("Has Azure certifications: AZ-900, Cloud Essentials+", infer=False)
add_memories("Career goal: transition to Director of Technology and Strategy role", infer=False)

# Technical Preferences  
add_memories("Strongly prefers PostgreSQL over MongoDB due to past negative experiences with MongoDB instability", infer=False)
add_memories("Uses macOS 15.4 with heavy keyboard text replacement usage for Obsidian formatting", infer=False)
add_memories("Prefers output formatted for Obsidian with YAML frontmatter by default", infer=False)

# Personal Projects
add_memories("Currently renovating home: furnace installation, laminate flooring, kitchen renovation, bathroom with heated flooring", infer=False)
add_memories("Building Swift web app for floorplan visualization with USD/USDZ upload and 3D navigation", infer=False)
```

**Best Practices:**
- Include specific entities (company names, technologies, locations)
- Add contextual details that aid semantic search
- Use consistent formatting for similar information types
- Include temporal markers when relevant

### **✅ Conversational Content (infer=true)**

**When to use:** Complex narratives needing analysis and relationship extraction

**Format patterns:**
```python
# Career Reflection
add_memories("I've been thinking about how my system design experience could translate into a strategic role. The SALTO Space deployment really opened my eyes to technology strategy.", infer=True)

# Technical Preference Explanation  
add_memories("Every time I work with MongoDB I remember why I avoid it. The UniFi controller issues were the latest reminder of why I stick with relational databases.", infer=True)

# Learning Process
add_memories("Working on the Microsoft 365 automation project taught me a lot about Power Automate workflows and how they can integrate with local tools like Obsidian.", infer=True)
```

**Best Practices:**
- Use natural language with context and relationships
- Include reasoning and background information
- Let the system extract and summarize key facts
- Provide enough detail for meaningful relationship detection

### **✅ Minimal Content (infer=true with auto-fallback)**

**Enhanced system handling:** Short content automatically falls back to raw storage

```python
# These will auto-fallback to infer=false
add_memories("PostgreSQL preferred", infer=True)  # → auto-fallback
add_memories("Summit Technology employee", infer=True)  # → auto-fallback  
add_memories("Blue.", infer=True)  # → auto-fallback
```

## 🔍 Search & Retrieval Optimization

### **Embedding-Friendly Text Patterns**

**✅ Include specific terminology:**
```python
# Good - Specific and searchable
"Uses PostgreSQL for database needs in personal projects"
"Experienced with Azure Active Directory and hybrid identity solutions"
"Prefers iPhone 15 Pro Max for mobile development and testing"

# Avoid - Too generic
"Likes databases"  
"Good with cloud stuff"
"Has phone"
```

**✅ Add relationship indicators:**
```python
# Explicit relationships
"Prefers PostgreSQL over MongoDB"
"Uses VS Code with Python extensions"  
"Works with Docker for local development"

# Temporal relationships
"Started at Summit Technology on December 4, 2024"
"Planning home renovation completion by spring 2025"
```

## 🛡️ Cross-Memory Safety

### **Enhanced System Protections**

The system now includes enhanced safeguards against inappropriate cross-memory operations:

**✅ Semantic Category Boundaries:**
- Technology ≠ Music ≠ Work ≠ Personal Life
- Only high similarity (>85%) allows cross-category relationships
- Conservative relationship detection prevents contamination

**✅ Example Safe Usage:**
```python
# These won't interfere with each other
add_memories("Works as Solutions Engineer at tech company", infer=False)  # Work
add_memories("Enjoys jazz music and classical concerts", infer=False)     # Personal
add_memories("Uses PostgreSQL for database projects", infer=False)        # Technical
add_memories("Renovating kitchen with modern appliances", infer=False)    # Home
```

## 📈 Optimal Usage Workflows

### **1. Initial Setup Phase**
```python
# Start with core structured facts
add_memories("Name: [User Name]", infer=False)
add_memories("Profession: [Role] at [Company]", infer=False)  
add_memories("Primary technologies: [Tech Stack]", infer=False)
add_memories("Key preferences: [Important Preferences]", infer=False)
```

### **2. Ongoing Usage**
```python
# Mix structured facts and conversational content
add_memories("Completed certification in Azure Security", infer=False)  # Fact
add_memories("The Azure security training really clarified my understanding of zero-trust architecture and how it applies to our client environments.", infer=True)  # Context
```

### **3. Project Documentation**
```python
# Document projects with both structure and context
add_memories("Project: Swift floorplan app with USD/USDZ support and 3D navigation", infer=False)
add_memories("Working on this floorplan app has been challenging but rewarding. The USD format integration is more complex than I expected, but the 3D visualization results are impressive.", infer=True)
```

## 🎯 Category Management

### **Automatic Categorization**

The system automatically generates categories based on content:

**Expected Categories:**
- `work` - Professional information
- `technology` - Technical skills and preferences  
- `personal` - Personal life and interests
- `health` - Health and wellness information
- `hobbies` - Personal interests and activities
- `processed` - Content processed with LLM inference
- `unprocessed` - Content stored as raw facts

### **Search by Category**
```python
# Search within specific categories
search_memory("PostgreSQL")  # Will find across all relevant categories
search_memory("work projects")  # Will focus on work-related memories
search_memory("personal preferences")  # Will focus on personal choices
```

## ⚡ Performance Optimization

### **Async Mode Usage**
```python
# For faster responses with background categorization
add_memories("Long detailed project description...", infer=True, async_mode=True)
```

**When to use async_mode:**
- Long content that needs processing
- When immediate response is needed
- Background categorization is acceptable

## 🧪 Testing & Validation

### **Recommended Test Patterns**

```python
# Test cross-category safety
add_memories("Enjoys classical music concerts", infer=True)  # Should not affect work memories
add_memories("Uses Docker for containerization", infer=True)  # Should not affect music memories

# Test minimal content handling
add_memories("Blue.", infer=True)  # Should auto-fallback successfully
add_memories("Happy.", infer=True)  # Should auto-fallback successfully

# Test structured vs conversational
add_memories("Prefers PostgreSQL database", infer=False)  # Structured
add_memories("I really prefer PostgreSQL because of my bad experiences with MongoDB.", infer=True)  # Conversational
```

## 📝 Migration from ChatGPT Memories

### **Conversion Strategy**

Based on the ChatGPT memory analysis, here's how to migrate structured memories:

```python
# High-priority memories (⭐⭐⭐⭐⭐) - Convert to structured facts
add_memories("Works for Summit Technology, a managed service provider (MSP) based in Salt Lake City, Utah", infer=False)
add_memories("Career trajectory: Solutions Engineer → Director of Technology and Strategy", infer=False)
add_memories("Strongly prefers PostgreSQL over MongoDB due to stability concerns", infer=False)

# Medium-priority memories (⭐⭐⭐) - Mix structured and conversational
add_memories("Currently renovating new home with multiple projects", infer=False)
add_memories("The home renovation has been a great learning experience, especially the furnace installation and kitchen design process.", infer=True)

# Context-dependent memories - Convert to conversational
add_memories("My experience with system design has really shaped how I think about technology strategy. The infrastructure work I've done gives me a different perspective on business decisions.", infer=True)
```

## 🔐 Data Quality Guidelines

### **✅ Do:**
- Be specific and factual
- Include relevant context
- Use consistent terminology
- Separate different types of information appropriately
- Trust the system's relationship detection

### **❌ Don't:**
- Force relationships between unrelated concepts
- Use overly generic language
- Mix multiple unrelated facts in single memories
- Assume the system will incorrectly categorize
- Over-engineer the input format

---

## Summary

The enhanced OpenMemory MCP server provides robust handling of structured data with built-in safeguards against common issues. External clients should focus on providing clear, well-structured input and trust the system's enhanced relationship detection and categorization capabilities.