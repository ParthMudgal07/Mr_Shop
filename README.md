# Mr.Shop 👕
### Conversational AI Fashion Stylist

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://mrshop-07.streamlit.app/)

Mr.Shop is a conversational AI fashion stylist designed to operate through Instagram DMs.

This project prototypes the **conversation layer** behind Mr.Shop using LangGraph. It focuses on understanding user intent, maintaining relevant context across turns through an ambient memory layer, and gracefully handling topic switches within the same conversation.

> **Note:** Streamlit is used only as a prototype interface to simulate the Instagram DM experience. The intended product experience is inside Instagram.

---

## ✨ Features

### 1. Intent Classification

The system identifies the user's current intent and routes the conversation to the appropriate agent.

Supported intents:

- **WARDROBE_UPLOAD** — Add, update, inspect, or manage wardrobe items
- **STYLING_ADVICE** — Outfit, fit, colour, and styling recommendations
- **PURCHASE** — Find, compare, or purchase fashion products
- **BOOKING** — Book or consult a human stylist or colour analyst

The intent classifier uses structured LLM output to ensure that the returned intent matches one of the supported categories.

---

### 2. Ambient Memory

Mr.Shop maintains lightweight user-specific context across conversation turns.

Currently stored information includes:

```text
Wardrobe
Preferences
Budget
```

For example:

```text
User: I like oversized clothes.

→ preferences:
  fit = oversized

User: My budget is ₹5000.

→ budget:
  5000
```

The user does not need to repeat these details in every message.

---

### 3. Multi-turn Context

The system uses the user's existing ambient memory when generating responses.

For example:

```text
User: I like oversized clothes.

Mr.Shop: Got it, I'll keep oversized fits in mind.

User: My budget is ₹5000.

Mr.Shop: Noted!

User: Find me a jacket.

Mr.Shop: I can help you find jackets within your ₹5000 budget
and look for oversized styles.
```

---

### 4. Graceful Topic Switching

Users can switch between functionalities without starting a new conversation.

Example:

```text
User → Styling:
"What should I wear to a casual dinner?"

        ↓

STYLING_ADVICE

        ↓

User → Purchase:
"Can I buy that jacket?"

        ↓

PURCHASE
```

The conversation remains within the same chat while the system updates the current intent and retains relevant ambient memory.

---

## 🧠 Architecture

The conversation layer is implemented using LangGraph.

```text
                 User Message
                      │
                      ▼
              Memory Extraction
                      │
                      ▼
               Memory Update
                      │
                      ▼
             Intent Classification
                      │
                      ▼
                    Router
          ┌───────────┼───────────┐
          │           │           │
          ▼           ▼           ▼
      Wardrobe     Styling     Purchase
      Agent        Agent       Agent
          │           │           │
          └───────────┼───────────┘
                      │
                      ▼
                  Response
```

The system maintains the following state:

```text
ShopState
├── messages
├── intent
├── memory_update
├── ambient_memory
└── response
```

---

## 🔄 Conversation Flow

For every user message:

```text
1. User sends a message
          ↓
2. Extract potentially useful user information
          ↓
3. Update ambient memory
          ↓
4. Classify the current intent
          ↓
5. Route to the appropriate agent
          ↓
6. Generate a response using:
      • Current user query
      • Ambient memory
      • Agent-specific instructions
          ↓
7. Return response to the chat interface
```

This allows the system to separate:

- **What the user currently wants** → Intent
- **What should be remembered about the user** → Ambient Memory
- **What should be said right now** → Agent Response

---

## 🛠️ Tech Stack

- **Python**
- **LangGraph** — workflow orchestration
- **LangChain** — LLM integration
- **OpenRouter** — LLM API provider
- **Gemma 4 26B A4B** — primary LLM
- **Pydantic** — structured outputs and state validation
- **Streamlit** — prototype chat interface

---

## 📁 Project Structure

```text
mr_shop/
│
├── app.py
├── graph.py
├── requirements.txt
├── .gitignore
└── README.md
```

`graph.py` contains the LangGraph workflow, intent classification, ambient memory handling, routing, and agent logic.

`app.py` provides the Streamlit interface that simulates the Instagram DM experience.

---

## 🚀 Running Locally

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd mr_shop
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```env
OPENROUTER_API_KEY=your_api_key
OPENROUTER_MODEL=google/gemma-4-26b-a4b-it:free
```

### 5. Run the application

```bash
streamlit run app.py
```

---

## 🌐 Live Demo

The current prototype is available here:

**[Open Mr.Shop Demo](https://mrshop-07.streamlit.app/)**

The Streamlit interface is a demonstration of how the Mr.Shop conversation layer could behave inside an Instagram DM environment.

---

## 📈 Scaling the Design

The current architecture is intentionally modular so additional Mr.Shop functionality can be added without redesigning the entire conversation layer.

For example, a future intent could be added:

```text
NEW INTENT
    ↓
Add intent to classifier schema
    ↓
Add routing destination
    ↓
Create new specialized agent
```

The ambient memory can also be extended with additional fields such as:

```text
preferences
├── fit
├── colours
├── brands
└── styles

wardrobe
├── tops
├── bottoms
├── footwear
└── accessories

budget
```

This allows new capabilities to be added while keeping the core conversation architecture unchanged.

---

## 🎯 Project Goal

The primary goal of this prototype is to demonstrate a lightweight conversational layer capable of:

- Understanding the user's current intent
- Remembering relevant user information
- Maintaining context across multiple turns
- Switching between functionalities naturally
- Routing requests to specialized agents
- Generating context-aware responses

The architecture can serve as the foundation for a larger Instagram-based Mr.Shop experience.
