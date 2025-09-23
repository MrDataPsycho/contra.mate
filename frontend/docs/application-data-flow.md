# Application Data Flow

This document explains how user requests are processed, served, and managed in our AI chat application, including the complete TypeScript data flow from frontend to GPT-5 and back.

## Overview

The application follows a client-server architecture with AI SDK integration:

```
User Input → React State → API Endpoint → AI SDK → GPT-5 → Response → React State → UI Rendering
```

## Data Flow Components

### 1. User Input Processing

**Entry Point**: `app/page.tsx:11` - Main chat interface
**Component**: `components/chat/chat-assistant.tsx:47` - Main chat logic
**State Management**: Uses React `useState` for messages array
**Input Capture**: `PromptInput` component captures user text

### 2. TypeScript Type Definitions

#### Frontend Message Type (`chat-assistant.tsx:30-45`)

```typescript
type ChatMessage = {
  id: string;                    // Unique identifier
  role: "user" | "assistant";    // Who sent the message
  content: string;               // The actual text
  sources?: Array<{              // Optional: web search sources
    url: string;
    title?: string;
  }>;
  toolCalls?: Array<{            // Optional: AI tool usage
    type: string;
    state: string;
    input?: any;                 // Tool input parameters
    output?: any;                // Tool output results
    errorText?: string;
  }>;
};
```

#### AI SDK Message Type (Internal)

```typescript
interface AIMessage {
  role: "user" | "assistant" | "system";
  content: string;
}
```

### 3. Request Flow

#### Step 1: User Message Creation (`chat-assistant.tsx:65-73`)

```typescript
const userMessage: ChatMessage = {
  id: Date.now().toString(),    // Unique ID using timestamp
  role: "user",
  content: message.text,
};

const updatedMessages = [...messages, userMessage];  // Spread existing + new
setMessages(updatedMessages);                        // Update state
```

#### Step 2: API Call (`chat-assistant.tsx:77-81`)

```typescript
const response = await fetch("/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    messages: updatedMessages  // ChatMessage[] type
  }),
});
```

### 4. Backend Processing

#### API Endpoint (`app/api/chat/route.ts`)

**Input Validation** (`route.ts:10-15`):
```typescript
if (!messages || !Array.isArray(messages) || messages.length === 0) {
  return NextResponse.json(
    { error: "Messages array is required" },
    { status: 400 }
  );
}
```

**Data Conversion** (`route.ts:17-21`):
```typescript
// Convert frontend format to AI SDK format
const aiMessages = messages.map((msg: any) => ({
  role: msg.role,      // Extract role: "user" | "assistant"
  content: msg.content // Extract content: string
}));
```

**AI Integration** (`route.ts:23-32`):
```typescript
const result = await generateText({
  model: openai("gpt-5"),           // GPT-5 model
  system: SYSTEM_INSTRUCTIONS,      // Travel agent prompt
  messages: aiMessages,             // AIMessage[]: Conversation
  tools: {                         // Tool configuration
    web_search: openai.tools.webSearch({
      searchContextSize: "low",
    }),
  },
});
```

### 5. AI SDK Integration

#### AI SDK Imports (`route.ts:2-3`)

```typescript
import { openai } from "@ai-sdk/openai";  // OpenAI provider
import { generateText } from "ai";        // Core AI SDK function
```

#### Tool Configuration

The application registers tools with the AI SDK:
- **Only tool available**: `web_search`
- **GPT-5 decides**: When and how to use tools based on system prompt
- **No application logic**: For tool selection

#### System Prompt Configuration (`components/agent/prompt.ts`)

The system prompt instructs GPT-5 on tool usage:
```typescript
const SYSTEM_INSTRUCTIONS = `
...
**Web Search Guidelines:**
- Once you have gathered at least the destination preferences, budget range, trip duration, and travel dates, you may use the web_search tool to find current information
- Use web search to find:
  - Current travel conditions, weather, and seasonal information
  - Up-to-date prices for flights, accommodations, and activities
...
`;
```

### 6. Response Generation and Mapping

#### AI SDK Response Type

```typescript
interface GenerateTextResult {
  text: string;                    // GPT-5 response text
  sources?: Array<{                // Web search sources (if tools used)
    url: string;
    title?: string;
  }>;
  steps?: Array<{                  // Tool execution steps
    type: string;                  // "web_search"
    state: string;                 // "completed" | "failed"
    input?: any;                   // Tool input parameters
    output?: any;                  // Tool output results
    errorText?: string;
  }>;
}
```

#### API Response Mapping (`route.ts:34-38`)

```typescript
return NextResponse.json({
  response: result.text,        // string
  sources: result.sources || [], // Array<{url: string, title?: string}>
  toolCalls: result.steps || [], // Array<{type: string, state: string, ...}>
});
```

#### Frontend Response Handling (`chat-assistant.tsx:86-93`)

```typescript
const assistantMessage: ChatMessage = {
  id: (Date.now() + 1).toString(),      // Generate new ID
  role: "assistant",                     // Set role
  content: data.response,                // Map: data.response → content
  sources: data.sources || [],           // Map: data.sources → sources
  toolCalls: data.toolCalls || [],       // Map: data.toolCalls → toolCalls
};
setMessages((prev) => [...prev, assistantMessage]); // Add to state
```

### 7. UI Rendering

#### Message Display (`chat-assistant.tsx:119-169`)

```typescript
{messages.map((message) => (
  <Message key={message.id} from={message.role}>
    <MessageContent>{message.content}</MessageContent>

    {/* Display tool calls if available */}
    {message.toolCalls && message.toolCalls.length > 0 && (
      <div className="mt-4">
        {message.toolCalls.map((toolCall, index) => (
          <Tool key={index} defaultOpen={toolCall.state === "output-available"}>
            <ToolHeader type={toolCall.type} state={toolCall.state} />
            <ToolContent>
              {toolCall.input && <ToolInput input={toolCall.input} />}
              {toolCall.output && <ToolOutput output={toolCall.output} />}
            </ToolContent>
          </Tool>
        ))}
      </div>
    )}

    {/* Display sources if available */}
    {message.sources && message.sources.length > 0 && (
      <div className="mt-4">
        <Sources>
          <SourcesTrigger count={message.sources.length} />
          <SourcesContent>
            {message.sources.map((source, index) => (
              <Source key={index} href={source.url} title={source.title || source.url} />
            ))}
          </SourcesContent>
        </Sources>
      </div>
    )}
  </Message>
))}
```

## Complete Data Flow Example

### Step-by-Step with Real Data

```typescript
// 1. FRONTEND: User types "I want to visit Paris in March"
const userMessage: ChatMessage = {
  id: "1693839600000",
  role: "user",
  content: "I want to visit Paris in March"
};

// 2. API CONVERSION: Strip extra fields for AI SDK
const aiMessages = [{
  role: "user",
  content: "I want to visit Paris in March"
}];

// 3. AI SDK PROCESSING: Send to GPT-5 with tools
const result = await generateText({
  model: openai("gpt-5"),
  messages: aiMessages,  // AIMessage[]
  tools: { web_search: ... }
});

// 4. AI SDK RETURNS: GPT-5 response with tool usage
const result = {
  text: "I'd love to help you plan your Paris trip! Based on current information, March is a great time to visit...",
  sources: [
    { url: "https://weather.com/paris", title: "Paris Weather" }
  ],
  steps: [
    {
      type: "web_search",
      state: "completed",
      input: { query: "Paris weather March 2025" },
      output: { results: [...] }
    }
  ]
};

// 5. API RESPONSE: Map to frontend format
return NextResponse.json({
  response: result.text,     // → content
  sources: result.sources,   // → sources
  toolCalls: result.steps    // → toolCalls
});

// 6. FRONTEND RECEIVES: Convert back to ChatMessage
const assistantMessage: ChatMessage = {
  id: "1693839600001",
  role: "assistant",
  content: "I'd love to help you plan your Paris trip! Based on current information, March is a great time to visit...",
  sources: [{ url: "https://weather.com/paris", title: "Paris Weather" }],
  toolCalls: [{
    type: "web_search",
    state: "completed",
    input: { query: "Paris weather March 2025" },
    output: { results: [...] }
  }]
};
```

## Memory and Persistence

### Current State Management

**❌ No Persistent Memory**: The application currently has no memory persistence:
- Messages stored only in React state (`useState`)
- Conversation history lost on page refresh
- No database, localStorage, or session storage implementation
- Each API call sends full conversation history from client state

### useState Conversation Management

#### State Structure
```typescript
const [messages, setMessages] = useState<ChatMessage[]>([]);
```
- **Initial state**: Empty array `[]`
- **Type**: Array of `ChatMessage` objects
- **Location**: Component-level state (not global)

#### Key useState Patterns

**Immutable Updates**:
```typescript
const updatedMessages = [...messages, newMessage];  // Spread existing + new
setMessages(updatedMessages);                        // Update state
```

**Functional Updates**:
```typescript
setMessages((prev) => [...prev, assistantMessage]);
```

## Tool Call Decision Making

### GPT-5 Autonomous Tool Selection

The **GPT-5 model** controls all tool usage decisions:

1. **Application Setup**: Registers available tools with AI SDK
2. **GPT-5 Decision Making**: Model decides when and how to use tools based on system prompt
3. **AI SDK Execution**: Handles tool execution automatically
4. **Application Display**: Shows tool usage results and sources

### Tool Call Flow

```
User Message → GPT-5 Analysis → Tool Decision → Tool Execution → Result Integration → Response
```

- **Zero application logic** for tool decisions
- **GPT-5 has full autonomy** over tool usage
- **System prompt provides guidelines** but model decides
- **AI SDK handles tool execution** automatically

## Key TypeScript Concepts

1. **Type Annotations**: `: ChatMessage` tells TypeScript what shape the data should have
2. **Optional Properties**: `sources?` means this field might not exist
3. **Union Types**: `"user" | "assistant"` means role can only be one of these strings
4. **Interface Mapping**: Converting between different object shapes while maintaining type safety
5. **Array Types**: `Array<{...}>` defines what each array element should look like
6. **Type Safety**: TypeScript catches errors if you try to access properties that don't exist

## Architecture Summary

- **Stateless API**: Each request includes full conversation context
- **Client-side state**: All conversation memory exists in React component state
- **AI SDK Integration**: Uses AI SDK 5 with non-streaming `generateText()`
- **Enhanced responses**: Supports sources and tool calls (web search)
- **Travel agent focus**: System prompt configured for travel planning assistance
- **Type Safety**: Complete TypeScript coverage for data flow integrity