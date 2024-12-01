"""
File: src/essay_writer.py
Author: Ramendra Tyagi
Created on: 11/19/2024 
Description: essay writer
"""

#Python
import os
from typing import Annotated, TypedDict
import operator
from typing import List, TypedDict, Annotated
from pydantic import BaseModel, Field
from uuid import uuid4
from dotenv import load_dotenv
_ = load_dotenv()
#LangChain
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage, ChatMessage
from langchain_openai import ChatOpenAI

# LangGraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
import operator
from langgraph.checkpoint.memory import MemorySaver
from src.prompts import *

from tavily import TavilyClient
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
memory = MemorySaver()

class Queries(BaseModel):
    queries: List[str]

class AgentState(TypedDict):
    task: str
    plan: str
    draft: str
    critique: str
    content: List[str]
    revision_number: int
    max_revisions: int


class EssayAgent():
    def __init__(self) -> None:
        builder = StateGraph(AgentState)
        builder.add_node("planner", self.plan_node)
        builder.add_node("generate", self.generation_node)
        builder.add_node("reflect", self.reflection_node)
        builder.add_node("research_plan", self.research_plan_node)
        builder.add_node("research_critique", self.research_critique_node)
        builder.set_entry_point("planner")
        builder.add_conditional_edges(
            "generate", 
            self.should_continue, 
            {END: END, "reflect": "reflect"}
        )
        builder.add_edge("planner", "research_plan")
        builder.add_edge("research_plan", "generate")
        builder.add_edge("reflect", "research_critique")
        builder.add_edge("research_critique", "generate")

        self.writer_agent = builder.compile(checkpointer=memory, interrupt_after=["planner","research_plan","generate","reflect","research_critique"])
    


    def plan_node(self,state: AgentState):
        print("Plan Node")
        messages = [
            SystemMessage(content=PLAN_PROMPT), 
            HumanMessage(content=state['task'])
        ]
        response = model.invoke(messages)
        return {"plan": response.content}

    def research_plan_node(self,state: AgentState):
        queries = model.with_structured_output(Queries).invoke([
            SystemMessage(content=RESEARCH_PLAN_PROMPT),
            HumanMessage(content=state['task'])
        ])
        content = []
        for q in queries:
            response = tavily.search(query=q, max_results=2)
            for r in response['results']:
                content.append(r['content'])
        return {"content": content}

    def generation_node(self,state: AgentState):
        print("Generate Node")
        content = "\n\n".join(state['content'] or [])
        user_message = HumanMessage(
            content=f"{state['task']}\n\nHere is my plan:\n\n{state['plan']}")
        messages = [
            SystemMessage(
                content=WRITER_PROMPT.format(content=content)
            ),
            user_message
            ]
        response = model.invoke(messages)
        return {
            "draft": response.content, 
            "revision_number": state.get("revision_number", 1) + 1
        }

    def reflection_node(self,state: AgentState):
        print("Reflect Node")
        messages = [
            SystemMessage(content=REFLECTION_PROMPT), 
            HumanMessage(content=state['draft'])
        ]
        response = model.invoke(messages)
        return {"critique": response.content}

    def research_critique_node(self,state: AgentState):
        print("Research Critique Node")
        queries = model.with_structured_output(Queries).invoke([
            SystemMessage(content=RESEARCH_CRITIQUE_PROMPT),
            HumanMessage(content=state['critique'])
        ])
        content = state['content'] or []
        for q in queries:
            response = tavily.search(query=q, max_results=2)
            for r in response['results']:
                content.append(r['content'])
        return {"content": content}


    def should_continue(self,state):
        print("Should contunue Node")
        if state["revision_number"] > state["max_revisions"]:
            return END
        return "reflect"    

    def write_essay(self,topic):
        state_output =[]
        thread = {"configurable": {"thread_id": "1"}}
        self.thread = thread
        for s in self.writer_agent.stream({
            'task': f"{topic}",
            "max_revisions": 2,
            "revision_number": 1,
        }, thread):
            state_output.append(s)
        print(f"Generate Step:{s}")
        while self.writer_agent.get_state(self.thread).next:
            print(f"Next Step loop")
        return state_output[-2]
    
    def next_step(self):
        state_output =[]
        for s in self.writer_agent.stream(None, self.thread):
            print(f"Next Step: {s}")
            state_output.append(s)
            
        return state_output[-2]