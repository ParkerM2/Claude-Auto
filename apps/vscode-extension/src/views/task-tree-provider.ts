import * as vscode from 'vscode';
import * as path from 'path';
import { Spec, Phase, Task, TaskStatus, BuildStatus } from '../types';
import { CLIClient } from '../backend/cli-client';

/**
 * Tree item types for the task tree hierarchy
 */
type TreeItemType = 'spec' | 'phase' | 'task';

/**
 * Tree item data for the task tree view
 * Represents a node in the tree (spec, phase, or task)
 */
interface TaskTreeItemData {
  type: TreeItemType;
  label: string;
  id: string;
  status?: TaskStatus | BuildStatus;
  spec?: Spec;
  phase?: Phase;
  task?: Task;
}

/**
 * Tree data provider for Auto Claude task list
 *
 * Displays specs with nested phases and subtasks in VS Code sidebar.
 * Implements VS Code's TreeDataProvider interface for the tree view.
 */
export class TaskTreeProvider implements vscode.TreeDataProvider<TaskTreeItemData> {
  private _onDidChangeTreeData: vscode.EventEmitter<TaskTreeItemData | undefined | null | void> =
    new vscode.EventEmitter<TaskTreeItemData | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<TaskTreeItemData | undefined | null | void> =
    this._onDidChangeTreeData.event;

  private specs: Spec[] = [];
  private cliClient: CLIClient;

  constructor(cliClient: CLIClient) {
    this.cliClient = cliClient;

    // Listen to backend events for real-time updates
    this.cliClient.on('progress', () => {
      this.refresh();
    });

    // Initial load of specs
    void this.loadSpecs();
  }

  /**
   * Refresh the tree view
   */
  refresh(): void {
    void this.loadSpecs();
    this._onDidChangeTreeData.fire();
  }

  /**
   * Load specs from backend via CLI client
   */
  private async loadSpecs(): Promise<void> {
    try {
      // Get list of specs from backend
      const specList = await this.cliClient.listSpecs();

      // TODO: Load full spec data for each spec
      // For now, we'll create minimal Spec objects from the list
      this.specs = specList.map(item => ({
        feature: item.name,
        workflow_type: 'feature',
        workflow_rationale: '',
        phases: [],
        summary: {
          total_phases: 0,
          total_subtasks: 0,
          services_involved: [],
        },
        status: item.status,
        planStatus: item.status,
        updated_at: item.lastUpdated,
        qa_signoff: null,
      }));
    } catch (error) {
      // If loading fails (e.g., no specs or backend not available), use empty array
      this.specs = [];
      console.error('Failed to load specs:', error);
    }
  }

  /**
   * Get tree item for a given element
   * Called by VS Code to render each node in the tree
   */
  getTreeItem(element: TaskTreeItemData): vscode.TreeItem {
    const treeItem = new vscode.TreeItem(
      element.label,
      this.getCollapsibleState(element)
    );

    // Set unique ID for the tree item
    treeItem.id = element.id;

    // Set icon based on type and status
    treeItem.iconPath = this.getIcon(element);

    // Set description (shown on the right side)
    treeItem.description = this.getDescription(element);

    // Set tooltip
    treeItem.tooltip = this.getTooltip(element);

    // Set context value for command targeting
    treeItem.contextValue = element.type;

    return treeItem;
  }

  /**
   * Get children of a tree item
   * Called by VS Code to populate tree hierarchy
   */
  getChildren(element?: TaskTreeItemData): Thenable<TaskTreeItemData[]> {
    if (!element) {
      // Root level: return specs
      return Promise.resolve(this.getSpecItems());
    }

    switch (element.type) {
      case 'spec':
        // Spec level: return phases
        return Promise.resolve(this.getPhaseItems(element.spec!));
      case 'phase':
        // Phase level: return tasks
        return Promise.resolve(this.getTaskItems(element.phase!));
      case 'task':
        // Task level: no children
        return Promise.resolve([]);
      default:
        return Promise.resolve([]);
    }
  }

  /**
   * Get spec items for root level
   */
  private getSpecItems(): TaskTreeItemData[] {
    return this.specs.map(spec => ({
      type: 'spec' as TreeItemType,
      label: spec.feature,
      id: `spec-${spec.feature}`,
      status: spec.status,
      spec,
    }));
  }

  /**
   * Get phase items for a spec
   */
  private getPhaseItems(spec: Spec): TaskTreeItemData[] {
    return spec.phases.map(phase => ({
      type: 'phase' as TreeItemType,
      label: phase.name,
      id: `phase-${phase.id}`,
      phase,
    }));
  }

  /**
   * Get task items for a phase
   */
  private getTaskItems(phase: Phase): TaskTreeItemData[] {
    return phase.subtasks.map(task => ({
      type: 'task' as TreeItemType,
      label: task.description,
      id: task.id,
      status: task.status,
      task,
    }));
  }

  /**
   * Determine collapsible state based on element type
   */
  private getCollapsibleState(element: TaskTreeItemData): vscode.TreeItemCollapsibleState {
    switch (element.type) {
      case 'spec':
        // Specs are collapsible if they have phases
        return element.spec && element.spec.phases.length > 0
          ? vscode.TreeItemCollapsibleState.Collapsed
          : vscode.TreeItemCollapsibleState.None;
      case 'phase':
        // Phases are collapsible if they have subtasks
        return element.phase && element.phase.subtasks.length > 0
          ? vscode.TreeItemCollapsibleState.Collapsed
          : vscode.TreeItemCollapsibleState.None;
      case 'task':
        // Tasks have no children
        return vscode.TreeItemCollapsibleState.None;
      default:
        return vscode.TreeItemCollapsibleState.None;
    }
  }

  /**
   * Get icon for tree item based on type and status
   */
  private getIcon(element: TaskTreeItemData): vscode.ThemeIcon {
    switch (element.type) {
      case 'spec':
        // Spec icons based on status
        switch (element.status) {
          case 'in_progress':
            return new vscode.ThemeIcon('sync~spin', new vscode.ThemeColor('charts.blue'));
          case 'completed':
            return new vscode.ThemeIcon('check', new vscode.ThemeColor('charts.green'));
          case 'failed':
            return new vscode.ThemeIcon('error', new vscode.ThemeColor('charts.red'));
          case 'paused':
            return new vscode.ThemeIcon('debug-pause', new vscode.ThemeColor('charts.orange'));
          case 'not_started':
            return new vscode.ThemeIcon('file-code', new vscode.ThemeColor('charts.gray'));
          default:
            return new vscode.ThemeIcon('file-code');
        }
      case 'phase':
        // Phase icon
        return new vscode.ThemeIcon('layers');
      case 'task':
        // Task icons based on status
        switch (element.status) {
          case 'pending':
          case 'not_started':
            return new vscode.ThemeIcon('circle-outline', new vscode.ThemeColor('charts.gray'));
          case 'in_progress':
            return new vscode.ThemeIcon('loading~spin', new vscode.ThemeColor('charts.yellow'));
          case 'completed':
            return new vscode.ThemeIcon('pass', new vscode.ThemeColor('charts.green'));
          case 'failed':
            return new vscode.ThemeIcon('issue-opened', new vscode.ThemeColor('charts.red'));
          case 'paused':
            return new vscode.ThemeIcon('debug-pause', new vscode.ThemeColor('charts.orange'));
          default:
            return new vscode.ThemeIcon('circle-outline');
        }
      default:
        return new vscode.ThemeIcon('question');
    }
  }

  /**
   * Get description text for tree item (shown on right side)
   */
  private getDescription(element: TaskTreeItemData): string | undefined {
    switch (element.type) {
      case 'spec':
        return this.formatSpecDescription(element.spec!);
      case 'phase':
        return this.formatPhaseDescription(element.phase!);
      case 'task':
        return this.formatTaskDescription(element.task!);
      default:
        return undefined;
    }
  }

  /**
   * Format spec description
   */
  private formatSpecDescription(spec: Spec): string {
    const parts: string[] = [];

    // Add phase count
    if (spec.summary.total_phases > 0) {
      parts.push(`${spec.summary.total_phases} phases`);
    }

    // Add task count
    if (spec.summary.total_subtasks > 0) {
      parts.push(`${spec.summary.total_subtasks} tasks`);
    }

    return parts.join(' • ');
  }

  /**
   * Format phase description
   */
  private formatPhaseDescription(phase: Phase): string {
    const completed = phase.subtasks.filter(t => t.status === 'completed').length;
    const total = phase.subtasks.length;
    return `${completed}/${total} tasks`;
  }

  /**
   * Format task description
   */
  private formatTaskDescription(task: Task): string {
    return task.service || '';
  }

  /**
   * Get tooltip for tree item
   */
  private getTooltip(element: TaskTreeItemData): string | vscode.MarkdownString {
    switch (element.type) {
      case 'spec':
        return this.formatSpecTooltip(element.spec!);
      case 'phase':
        return this.formatPhaseTooltip(element.phase!);
      case 'task':
        return this.formatTaskTooltip(element.task!);
      default:
        return '';
    }
  }

  /**
   * Format spec tooltip
   */
  private formatSpecTooltip(spec: Spec): vscode.MarkdownString {
    const tooltip = new vscode.MarkdownString();
    tooltip.appendMarkdown(`**${spec.feature}**\n\n`);
    tooltip.appendMarkdown(`**Status:** ${spec.status}\n\n`);
    tooltip.appendMarkdown(`**Type:** ${spec.workflow_type}\n\n`);
    if (spec.workflow_rationale) {
      tooltip.appendMarkdown(`**Rationale:** ${spec.workflow_rationale}\n\n`);
    }
    tooltip.appendMarkdown(`**Updated:** ${new Date(spec.updated_at).toLocaleString()}`);
    return tooltip;
  }

  /**
   * Format phase tooltip
   */
  private formatPhaseTooltip(phase: Phase): vscode.MarkdownString {
    const tooltip = new vscode.MarkdownString();
    tooltip.appendMarkdown(`**${phase.name}**\n\n`);
    tooltip.appendMarkdown(`**Type:** ${phase.type}\n\n`);
    tooltip.appendMarkdown(`**Description:** ${phase.description}\n\n`);

    const completed = phase.subtasks.filter(t => t.status === 'completed').length;
    const inProgress = phase.subtasks.filter(t => t.status === 'in_progress').length;
    const pending = phase.subtasks.filter(t => t.status === 'pending').length;
    const failed = phase.subtasks.filter(t => t.status === 'failed').length;

    tooltip.appendMarkdown(`**Progress:**\n`);
    tooltip.appendMarkdown(`- ✅ Completed: ${completed}\n`);
    if (inProgress > 0) tooltip.appendMarkdown(`- ⏳ In Progress: ${inProgress}\n`);
    if (pending > 0) tooltip.appendMarkdown(`- ⏸️ Pending: ${pending}\n`);
    if (failed > 0) tooltip.appendMarkdown(`- ❌ Failed: ${failed}\n`);

    return tooltip;
  }

  /**
   * Format task tooltip
   */
  private formatTaskTooltip(task: Task): vscode.MarkdownString {
    const tooltip = new vscode.MarkdownString();
    tooltip.appendMarkdown(`**${task.description}**\n\n`);
    tooltip.appendMarkdown(`**ID:** ${task.id}\n\n`);
    tooltip.appendMarkdown(`**Status:** ${task.status}\n\n`);
    tooltip.appendMarkdown(`**Service:** ${task.service}\n\n`);

    if (task.notes) {
      tooltip.appendMarkdown(`**Notes:** ${task.notes}\n\n`);
    }

    if (task.files_to_create.length > 0) {
      tooltip.appendMarkdown(`**Files to Create:**\n`);
      task.files_to_create.forEach(file => {
        tooltip.appendMarkdown(`- ${file}\n`);
      });
      tooltip.appendMarkdown('\n');
    }

    if (task.files_to_modify.length > 0) {
      tooltip.appendMarkdown(`**Files to Modify:**\n`);
      task.files_to_modify.forEach(file => {
        tooltip.appendMarkdown(`- ${file}\n`);
      });
      tooltip.appendMarkdown('\n');
    }

    if (task.verification) {
      tooltip.appendMarkdown(`**Verification:** ${task.verification.type}\n`);
    }

    return tooltip;
  }

  /**
   * Dispose resources
   */
  dispose(): void {
    this._onDidChangeTreeData.dispose();
  }
}
