/**
 * Task Manager - Multi-agent ADK application in TypeScript.
 *
 * Demonstrates:
 * - LlmAgent with FunctionTool and Zod schemas
 * - SequentialAgent pipeline (planner -> executor -> reviewer)
 * - Callbacks for guardrails
 * - State management via outputKey and instruction templating
 */

import {
  LlmAgent,
  SequentialAgent,
  FunctionTool,
  type CallbackContext,
} from '@google/adk';
import type { Content } from '@google/genai';
import { z } from 'zod';

// --- Tools ---

const createTask = new FunctionTool({
  name: 'create_task',
  description: 'Create a new task with a title, description, and priority.',
  parameters: z.object({
    title: z.string().describe('Short task title'),
    description: z.string().describe('Detailed task description'),
    priority: z.enum(['low', 'medium', 'high', 'critical']).describe('Task priority level'),
  }),
  execute: async ({ title, description, priority }) => {
    const id = `TASK-${Math.floor(Math.random() * 9000) + 1000}`;
    return {
      id,
      title,
      description,
      priority,
      status: 'created',
      created_at: new Date().toISOString(),
    };
  },
});

const listTasks = new FunctionTool({
  name: 'list_tasks',
  description: 'List all tasks, optionally filtered by status.',
  parameters: z.object({
    status: z.enum(['all', 'created', 'in_progress', 'done'])
      .optional()
      .describe('Filter tasks by status'),
  }),
  execute: async ({ status }) => {
    const tasks = [
      { id: 'TASK-001', title: 'Set up CI/CD', priority: 'high', status: 'in_progress' },
      { id: 'TASK-002', title: 'Write unit tests', priority: 'medium', status: 'created' },
      { id: 'TASK-003', title: 'Update docs', priority: 'low', status: 'done' },
    ];
    const filtered = status && status !== 'all'
      ? tasks.filter(t => t.status === status)
      : tasks;
    return { tasks: filtered, total: filtered.length };
  },
});

const estimateEffort = new FunctionTool({
  name: 'estimate_effort',
  description: 'Estimate the effort required for a task in hours.',
  parameters: z.object({
    task_description: z.string().describe('Description of the task to estimate'),
    complexity: z.enum(['simple', 'moderate', 'complex']).describe('Task complexity'),
  }),
  execute: async ({ task_description, complexity }) => {
    const baseHours: Record<string, number> = { simple: 2, moderate: 8, complex: 24 };
    const hours = baseHours[complexity] || 8;
    return {
      task: task_description,
      complexity,
      estimated_hours: hours,
      confidence: complexity === 'simple' ? 'high' : complexity === 'moderate' ? 'medium' : 'low',
    };
  },
});

// --- Callbacks ---

function beforeAgentCallback(callbackContext: CallbackContext): Content | undefined {
  console.log(`[Callback] Entering agent: ${callbackContext.agentName}`);
  return undefined; // Proceed normally
}

function beforeModelCallback({
  context,
  request,
}: {
  context: CallbackContext;
  request: any;
}): any | undefined {
  console.log(`[Callback] Before model call for: ${context.agentName}`);

  // Safety guardrail: block if "BLOCK" keyword detected
  const lastMessage = request.contents?.at(-1)?.parts?.[0]?.text ?? '';
  if (lastMessage.toUpperCase().includes('BLOCK')) {
    return {
      content: {
        role: 'model' as const,
        parts: [{ text: 'Request blocked by safety guardrail.' }],
      },
    };
  }

  return undefined; // Proceed normally
}

// --- Agents ---

// Stage 1: Planner - analyzes request and creates tasks
const planner = new LlmAgent({
  name: 'planner',
  model: 'gemini-2.0-flash',
  instruction: `You are a project planner. When given a project or goal:
1. Break it down into individual tasks using create_task
2. Use estimate_effort to estimate each task
3. Summarize the plan with tasks and total estimated hours

Always create at least 2 tasks for any project.`,
  description: 'Breaks down projects into tasks with effort estimates',
  tools: [createTask, estimateEffort],
  outputKey: 'project_plan',
  beforeAgentCallback,
  beforeModelCallback,
});

// Stage 2: Executor - organizes and prioritizes
const executor = new LlmAgent({
  name: 'executor',
  model: 'gemini-2.0-flash',
  instruction: `You are a project executor. Based on this project plan:

{project_plan}

1. List all existing tasks using list_tasks
2. Organize the new tasks by priority (critical > high > medium > low)
3. Create a recommended execution order
4. Identify any dependencies between tasks`,
  description: 'Organizes tasks and creates execution schedule',
  tools: [listTasks],
  outputKey: 'execution_plan',
  beforeAgentCallback,
});

// Stage 3: Reviewer - reviews the plan
const reviewer = new LlmAgent({
  name: 'reviewer',
  model: 'gemini-2.0-flash',
  instruction: `You are a project reviewer. Review this execution plan:

{execution_plan}

Evaluate:
1. Are priorities correctly assigned?
2. Is the effort estimation reasonable?
3. Are there missing tasks or dependencies?

Score 1-10 and provide brief feedback. If score >= 8, respond with "APPROVED".`,
  description: 'Reviews and scores the project plan',
  outputKey: 'review_result',
  beforeAgentCallback,
});

// Root agent: Sequential pipeline
export const rootAgent = new SequentialAgent({
  name: 'task_manager_pipeline',
  description: 'Task manager that plans, organizes, and reviews project tasks',
  subAgents: [planner, executor, reviewer],
});
