# AI & Quality Engineering Portfolio

Hi, I'm BBopaiahh B.P

I have 12+ years of experience in software testing, automation and QA leadership. Over the last few years, I have also been spending time learning and building projects around Generative AI, LLMs, AI testing and AI Agents.

This repository contains some of the AI projects I have built as hands on POCs.

My main goal with these projects was simple: instead of only learning AI concepts, I wanted to actually build something, test it, find where it fails and understand how it could be used in a real business situation.

---

# My AI Projects

I have divided the projects into two groups.

##  AI Agents

These projects can understand a request and take actions or carry out a workflow.

###  Bumblebee — BFSI Smart Assistant

A voice-based AI agent for banking, insurance and financial-services related questions.

I built this using ElevenLabs Agents.

The agent can:

- Understand what the customer is asking
- Look for information from its knowledge base
- Explain the information in simple language
- Have a voice conversation with the customer
- Handle questions it is not designed to answer
- Avoid giving personal financial advice
- Avoid handling account-specific information
- Direct the customer to the appropriate official channel when required

[View Bumblebee Project →](./ai-agents/01-bumblebee-bfsi-agent/README.md)

---

### NovaFin — Invoice Payment Agent

An AI agent that helps automate overdue invoice reminders.

I built this using Zapier Agents, Google Sheets and Gmail.

The basic idea is:

A spreadsheet contains customer invoices. The agent checks the invoices and looks for invoices that are unpaid, overdue and have not already received a reminder.

If an invoice matches those conditions, the agent:

1. Checks that the required information is available.
2. Creates a payment reminder email.
3. Sends the email to the customer.
4. Updates the spreadsheet after the email is successfully sent.
5. Skips invoices that have already been reminded.

I also added handling for missing information and email failures.

[View NovaFin Project →](./ai-agents/02-novafin-invoice-agent/README.md)

---

#  AI Assistants

These projects are focused more on helping a person understand, analyse or work with information.

###  The Judge — AI Configuration Drift Auditor

This is an AI assistant I built around a Quality Engineering problem.

In a large application, different customers or environments can have different configurations. Manually comparing those configurations can become difficult when there are many settings.

The Judge is designed to help compare configurations and identify differences that may need attention.

The project focuses on:

- Comparing configurations
- Looking for differences
- Analysing configuration drift
- Helping QA and engineering teams understand what changed
- Making the comparison easier to review

[View The Judge Project →](./ai-assistants/01-the-judge/README.md)

---

### RARE — Requirement Analysis & Response Engine

RARE stands for Requirement Analysis and Response Engine.

I built this as an experiment to see how an LLM could help with understanding software requirements.

The application allows a user to provide requirement documents and then uses AI to analyse the content and respond to questions.

The project includes:

- Document reading
- PDF and DOCX processing
- Text chunking
- LLM-based analysis
- Retrieval-based understanding
- AI-generated responses
- A simple Streamlit interface

[View RARE Project →](./ai-assistants/02-rare-requirement-assistant/README.md)

---

# Why I Built These Projects

My background is mainly in Quality Engineering and test automation.
I didn't want my AI learning to remain limited to courses and theory. I wanted to understand what happens when AI is actually used inside a workflow.

While building these projects, I focused on questions such as:
- Can the AI understand the user's request correctly?
- Where does the information come from?
- What happens if the information is missing?
- What happens when the user asks something outside the scope?
- Can the AI take an action safely?
- What happens when an action fails?
- How do we test an AI system when the answer is not always exactly the same?
- How can we stop the AI from making up information?
- What would need to change before using something like this in production?

These are the areas where I found my Quality Engineering background especially useful.

---

# My Technical Areas

### Quality Engineering

- Manual Testing
- Test Automation
- API Testing
- Playwright
- Python
- Pytest
- Postman
- Jenkins
- GitHub Actions
- CI/CD
- Agile / Scrum
- QA Leadership

### AI / GenAI

- Generative AI
- LLMs
- RAG
- AI Agents
- AI Assistants
- LLMOps
- AI Testing
- LangChain
- LangGraph
- DeepEval
- Embeddings
- Knowledge Graphs

---

# How I Approach AI Projects

I generally follow a simple approach:
**Understand the problem**
          ↓
**Decide where AI actually helps**
          ↓
**Build a small working POC**
          ↓
**Connect the required tools or data**
          ↓
**Add rules and guardrails**
          ↓
**Test normal and abnormal scenarios**
          ↓
**Find where it fails**
          ↓
**Improve the workflow**

This portfolio is a record of that learning process.

---

# What You Will Find Inside Each Project

For each project, I have documented:

- What problem I was trying to solve
- Why I built it
- How it works
- The tools I used
- The workflow
- Important configurations
- How I tested it
- Problems I found
- Limitations of the current POC
- What I would improve in a real production system
- My contribution to the project

I have also included screenshots and examples wherever possible so the projects can be understood without simply taking my word for it.

---

# A Note About These Projects

These are personal proof-of-concept projects created for learning, experimentation and demonstrating practical skills.

They are not official products or deployments of any company, government organisation or financial institution mentioned in the individual project examples.

---

# Contact

GitHub: [My GitHub Profile]

LinkedIn: [My LinkedIn Profile]

Email: [My Email]
