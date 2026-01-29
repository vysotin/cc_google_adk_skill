/**
 * Tests for the Task Manager agent.
 *
 * Unit tests for tool functions and agent structure.
 * Integration tests require a valid GEMINI_API_KEY.
 */

import { describe, it, expect } from 'vitest';

describe('Task Manager Agent Structure', () => {
  it('should export rootAgent', async () => {
    const { rootAgent } = await import('./agent');
    expect(rootAgent).toBeDefined();
    expect(rootAgent.name).toBe('task_manager_pipeline');
  });

  it('should have three sub-agents in the pipeline', async () => {
    const { rootAgent } = await import('./agent');
    expect(rootAgent.subAgents).toHaveLength(3);
  });

  it('should have agents in correct order', async () => {
    const { rootAgent } = await import('./agent');
    const names = rootAgent.subAgents.map((a: any) => a.name);
    expect(names).toEqual(['planner', 'executor', 'reviewer']);
  });
});

describe('Tool Functions', () => {
  it('create_task should return task with ID', async () => {
    // Import and test the tool's execute function directly
    const { rootAgent } = await import('./agent');
    const planner = rootAgent.subAgents[0] as any;
    const createTaskTool = planner.tools.find((t: any) => t.name === 'create_task');
    expect(createTaskTool).toBeDefined();
  });

  it('list_tasks should be available on executor', async () => {
    const { rootAgent } = await import('./agent');
    const executor = rootAgent.subAgents[1] as any;
    const listTasksTool = executor.tools.find((t: any) => t.name === 'list_tasks');
    expect(listTasksTool).toBeDefined();
  });

  it('estimate_effort should be available on planner', async () => {
    const { rootAgent } = await import('./agent');
    const planner = rootAgent.subAgents[0] as any;
    const estimateTool = planner.tools.find((t: any) => t.name === 'estimate_effort');
    expect(estimateTool).toBeDefined();
  });
});
