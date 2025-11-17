#!/usr/bin/env python3
"""
AI-Powered Research Workflow Demo

This demo showcases an AI-powered multi-agent research system inspired by
Anthropic's approach:

1. PLAN: AI analyzes research question and decomposes into subtopics
2. EXPLORE: Multiple agents work in parallel on different subtopics
3. SYNTHESIZE: Aggregate findings into final comprehensive answer

The AI dynamically decides:
- How many sub-agents to spawn (2-6)
- What specific topic each agent should explore
- How to best parallelize the research

Usage:
    # Uses the internal agent system (claude, codex, or copilot CLI)
    uv run python -m plugins.automation.workflows.examples.demo_ai_research
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.automation.workflows.engine import WorkflowEngine
from plugins.automation.workflows.definition import WorkflowDefinition
from plugins.automation.workflows.steps.operations.schemas import (
    get_decompose_result,
    get_subtopics,
    get_loop_result,
    get_exploration_findings,
)


async def main():
    print("\n" + "=" * 80)
    print("AI-POWERED MULTI-AGENT RESEARCH SYSTEM")
    print("=" * 80 + "\n")

    print("This demo showcases Anthropic-style multi-agent research:")
    print("1. PLAN: AI decomposes research question into subtopics")
    print("2. EXPLORE: Multiple agents work in parallel")
    print("3. SYNTHESIZE: Aggregate findings into final answer\n")

    # Create research workflow
    workflow_yaml = """
workflow:
  name: ai_research_system
  version: 1.0
  description: |
    Multi-agent research system with AI-powered task decomposition.

    Flow:
    1. PLAN: AI analyzes question and creates exploration tasks
    2. EXPLORE: Agents work in parallel on subtopics
    3. SYNTHESIZE: Aggregate findings into comprehensive answer

  inputs:
    question:
      type: string
      required: true
      description: The question to investigate

  outputs:
    final_report:
      type: string
      description: Synthesized findings

  steps:
    # PLAN PHASE: AI decomposes question into subtopics
    - id: decompose_question
      type: transform
      config:
        operation: decompose
        min_subtopics: 2
        max_subtopics: 5
        cli_type: claude
        model: haiku
      inputs:
        question: "{{ inputs.question }}"

    # EXPLORE PHASE: Multiple agents work in parallel
    - id: parallel_exploration
      type: loop
      depends_on: [decompose_question]
      items: "{{ steps.decompose_question.result.subtopics }}"
      item_var: subtopic
      steps:
        - id: explore_subtopic
          type: agent
          agent: explore
          operation: explore
          config:
            cli_type: claude
            model: haiku
          inputs:
            question: "{{ subtopic.exploration_task }}"

    # SYNTHESIZE PHASE: Aggregate exploration count
    - id: synthesize_findings
      type: transform
      depends_on: [parallel_exploration]
      config:
        operation: aggregate
        function: count
      inputs:
        items: "{{ steps.parallel_exploration.result.results }}"
"""

    try:
        print("📋 Parsing workflow definition...\n")
        workflow = WorkflowDefinition.from_yaml(workflow_yaml)

        errors = workflow.validate()
        if errors:
            print("❌ Validation errors:")
            for error in errors:
                print(f"   • {error}")
            return

        print("✅ Workflow validated\n")

        # Example question
        question = "How does the MCP workflow system handle dynamic parallelism?"

        print("=" * 80)
        print("RESEARCH QUESTION")
        print("=" * 80 + "\n")
        print(f"❓ {question}\n")

        inputs = {"question": question}

        print("🤖 PHASE 1: AI Planning - Decomposing research question...\n")

        engine = WorkflowEngine()

        # Execute with session persistence enabled
        result = await engine.execute(workflow, inputs, persist=True)

        # Show session info
        print(f"\n💾 SESSION PERSISTENCE")
        print(f"   Execution ID: {result.execution_id}")
        print(f"   Workflow Status: {result.status.value}")
        print(f"   All intermediate results are stored in: ~/.mcp/workflows/sessions/")

        # List recent workflow sessions
        sessions = engine.list_workflow_sessions(workflow_name="ai_research_system", limit=5)
        if sessions:
            latest_session = sessions[0]
            print(f"   Latest Session ID: {latest_session['session_id']}")
            print(f"   Last Step: {latest_session.get('last_completed_step', 'N/A')}")
        print()

        # Show decomposition using schema helper functions
        if "decompose_question" in result.step_results:
            decompose_result = get_decompose_result(
                result.step_results["decompose_question"].result
            )
            if decompose_result:
                subtopics = get_subtopics(decompose_result)
                reasoning = decompose_result["reasoning"]
                print(f"✅ AI created {len(subtopics)} research subtopics:\n")

                for idx, subtopic in enumerate(subtopics, 1):
                    title = subtopic["title"]
                    task = subtopic["exploration_task"]
                    importance = subtopic["importance"]
                    print(f"   {idx}. {title} [{importance}]")
                    print(f"      → {task}")

                if reasoning:
                    print(f"\n💭 AI Decomposition Strategy:")
                    print(f"   {reasoning}\n")

        # Show exploration phase using schema helper functions
        print("🔍 PHASE 2: Parallel Exploration - Agents working...\n")

        if "parallel_exploration" in result.step_results:
            loop_result = get_loop_result(
                result.step_results["parallel_exploration"].result
            )
            if loop_result:
                iterations = loop_result["iterations"]
                successful = loop_result["successful"]
                print(f"✅ Completed {successful}/{iterations} explorations\n")

                # Show exploration results using helper function
                # DEBUG: Let's see what's actually in loop_result
                print(f"\n[DEBUG] Loop result keys: {loop_result.keys()}")
                print(f"[DEBUG] Number of iterations: {len(loop_result['results'])}")
                for i, iteration in enumerate(loop_result['results']):
                    print(f"[DEBUG] Iteration {i}: status={iteration.get('status')}, step_results keys={list(iteration.get('step_results', {}).keys())}")
                    for step_id, step_res in iteration.get('step_results', {}).items():
                        print(f"[DEBUG]   Step {step_id}: type={type(step_res)}, has result={hasattr(step_res, 'result')}")
                        if hasattr(step_res, 'result'):
                            print(f"[DEBUG]   Result type: {type(step_res.result)}, value preview: {str(step_res.result)[:100]}")
                print()

                findings = get_exploration_findings(loop_result)
                print(f"📋 Exploration Findings ({len(findings)} found):\n")

                if findings:
                    for idx, finding in enumerate(findings, 1):
                        subtopic_title = (
                            subtopics[idx - 1]["title"]
                            if idx <= len(subtopics)
                            else f"Subtopic {idx}"
                        )

                        print(f"   {idx}. {subtopic_title}")

                        # Handle different finding types
                        if isinstance(finding, str) and finding:
                            # String result - show preview
                            finding_preview = (
                                finding[:300] + "..." if len(finding) > 300 else finding
                            )
                            print(f"      {finding_preview}\n")
                        elif isinstance(finding, dict):
                            # Dict result - try to extract meaningful content
                            # First check common exploration result keys
                            content = None
                            if 'answer' in finding:
                                content = finding['answer']
                            elif 'result' in finding:
                                content = finding['result']
                            elif 'finding' in finding:
                                content = finding['finding']
                            elif 'response' in finding:
                                content = finding['response']

                            if content and isinstance(content, str):
                                content_preview = content[:300] + "..." if len(content) > 300 else content
                                print(f"      {content_preview}\n")
                            elif content:
                                # Non-string content
                                content_str = str(content)
                                content_preview = content_str[:300] + "..." if len(content_str) > 300 else content_str
                                print(f"      {content_preview}\n")
                            else:
                                # Show structure
                                print(f"      [Dict with keys: {', '.join(finding.keys())}]")
                                # Show first few items for debugging
                                import json
                                dict_preview = json.dumps(finding, indent=2, default=str)[:300]
                                print(f"      {dict_preview}...\n")
                        else:
                            print(f"      [Result type: {type(finding).__name__}]\n")
                else:
                    print("   [No findings extracted - check schema helper function]\n")

        # Show synthesis
        print("📊 PHASE 3: Synthesis - Aggregating findings...\n")

        if "synthesize_findings" in result.step_results:
            synth_result = result.step_results["synthesize_findings"].result
            # Extract count from aggregate result
            if isinstance(synth_result, dict):
                count = synth_result.get("result", synth_result.get("item_count", 0))
            else:
                count = synth_result
            print(f"✅ Research Complete - Aggregated {count} exploration results!\n")

        # Show session persistence summary
        print("=" * 80)
        print("SESSION PERSISTENCE SUMMARY")
        print("=" * 80 + "\n")

        if sessions:
            latest = sessions[0]
            print(f"📁 Session Details:")
            print(f"   ID: {latest['session_id']}")
            print(f"   Status: {latest['status']}")
            print(f"   Created: {latest['created_at']}")
            print(f"   Last Updated: {latest['updated_at']}\n")

            print("💡 You can access persisted data:")
            print(f"   • All step results are saved")
            print(f"   • Agent exploration findings are preserved")
            print(f"   • Context and outputs are recoverable")
            print(f"   • Session can be resumed or inspected later\n")

            # Show how to load session data
            print("🔍 To inspect session data programmatically:")
            print(f"   ```python")
            print(f"   engine = WorkflowEngine()")
            print(f"   context, metadata = engine.load_from_session('{latest['session_id']}')")
            print(f"   print(metadata['last_completed_step'])")
            print(f"   print(context.step_results.keys())")
            print(f"   ```\n")

        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
