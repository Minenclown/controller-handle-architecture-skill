/**
 * Controller-Handle Architecture — TypeScript Template
 *
 * This template illustrates the Controller-Handle pattern for TypeScript.
 * It uses abstract domain names so you can adapt it to any project.
 *
 * Structure:
 *   1. Controller base class
 *   2. HandleBase interface
 *   3. Domain-specific handle interface
 *   4. Concrete handle implementation(s)
 *   5. Domain controller
 *   6. ControllerRegistry (composition root)
 *   7. initControllers() — idempotent bootstrap
 *
 * Note: The `Map` built-in preserves insertion order in JavaScript, so
 * iterating over `this.handles` returns items in the order they were
 * registered.
 */

// =====================================================================
// 1. Controller Base
// =====================================================================

export abstract class Controller<H extends HandleBase> {
  protected readonly name: string;
  protected readonly handles: Map<string, H> = new Map();

  constructor(name: string = "") {
    this.name = name || this.constructor.name;
  }

  /** Register a handle. Throws if a handle with the same id already exists. */
  register(handle: H): void {
    const id = handle.getId();
    if (this.handles.has(id)) {
      throw new Error(`${this.name}: Handle '${id}' already registered`);
    }
    this.handles.set(id, handle);
  }

  /** Retrieve a handle by id. Throws if the id is unknown. */
  getHandle(id: string): H {
    const handle = this.handles.get(id);
    if (!handle) {
      throw new Error(`${this.name}: Unknown handle '${id}'`);
    }
    return handle;
  }

  /** Returns true if a handle with the given id is registered. */
  hasHandle(id: string): boolean {
    return this.handles.has(id);
  }

  /** Return all registered handles (insertion order preserved by Map). */
  getHandles(): H[] {
    return Array.from(this.handles.values());
  }

  /** Return all registered handle ids (insertion order preserved by Map). */
  getHandleIds(): string[] {
    return Array.from(this.handles.keys());
  }

  /** Remove a handle by id. No-op if the id was never registered. */
  unregister(id: string): void {
    this.handles.delete(id);
  }
}

// =====================================================================
// 2. HandleBase Interface
// =====================================================================

/**
 * Every handle must implement this minimal contract.
 * The `id` uniquely identifies the handle within its controller;
 * `getDisplayName()` is intended for UI / logging purposes.
 */
export interface HandleBase {
  getId(): string;
  getDisplayName(): string;
}

// =====================================================================
// 3. Domain-Specific Handle Interface
// =====================================================================

/**
 * Example domain interface for a "search" domain.
 * Replace this (and the concrete implementations below) with the
 * domain-specific contract you need for your project.
 */
export interface SearchHandle extends HandleBase {
  search(query: string, limit?: number, ...kwargs: any[]): any[];
}

// =====================================================================
// 4. Concrete Handle Implementations
// =====================================================================

/** Example concrete handle — adapt to your real implementation. */
class SemanticSearchHandle implements SearchHandle {
  getId(): string {
    return "semantic";
  }

  getDisplayName(): string {
    return "Semantic Search";
  }

  search(query: string, limit: number = 20, ..._kwargs: any[]): any[] {
    // Replace with actual semantic-search logic.
    return [];
  }
}

/** Example concrete handle — adapt to your real implementation. */
class KeywordSearchHandle implements SearchHandle {
  getId(): string {
    return "keyword";
  }

  getDisplayName(): string {
    return "Keyword Search";
  }

  search(query: string, limit: number = 20, ..._kwargs: any[]): any[] {
    // Replace with actual keyword-search logic.
    return [];
  }
}

/** Example concrete handle — adapt to your real implementation. */
class HybridSearchHandle implements SearchHandle {
  getId(): string {
    return "hybrid";
  }

  getDisplayName(): string {
    return "Hybrid Search";
  }

  search(query: string, limit: number = 20, ..._kwargs: any[]): any[] {
    // Replace with actual hybrid-search logic.
    return [];
  }
}

// =====================================================================
// 5. Domain Controller
// =====================================================================

/**
 * Concrete controller for the search domain.
 * Thin façade that delegates to the appropriate handle.
 */
export class SearchController extends Controller<SearchHandle> {
  constructor() {
    super("SearchController");
  }

  /** Run a search on a single handle identified by `handleId`. */
  search(
    handleId: string,
    query: string,
    limit: number = 20,
    ...kwargs: any[]
  ): any[] {
    return this.getHandle(handleId).search(query, limit, ...kwargs);
  }

  /** Run a search across *every* registered handle. */
  searchAll(
    query: string,
    limit: number = 20,
    ...kwargs: any[]
  ): Record<string, any[]> {
    const results: Record<string, any[]> = {};
    for (const handle of this.getHandles()) {
      results[handle.getId()] = handle.search(query, limit, ...kwargs);
    }
    return results;
  }
}

// =====================================================================
// 6. ControllerRegistry (Composition Root)
// =====================================================================

/**
 * Singleton registry that owns all controller instances.
 * Use this as the single entry point for obtaining controllers at
 * runtime; it keeps the dependency graph explicit and testable.
 */
export class ControllerRegistry {
  private static _instance: ControllerRegistry | null = null;
  private controllers: Map<string, Controller<any>> = new Map();

  /** Return the shared singleton instance (lazy-initialised). */
  static getInstance(): ControllerRegistry {
    if (!ControllerRegistry._instance) {
      ControllerRegistry._instance = new ControllerRegistry();
    }
    return ControllerRegistry._instance;
  }

  /** Register a controller by logical name. Throws on duplicate. */
  registerController(name: string, controller: Controller<any>): void {
    if (this.controllers.has(name)) {
      throw new Error(`Controller '${name}' already registered`);
    }
    this.controllers.set(name, controller);
  }

  /** Retrieve a controller by name. Throws if the name is unknown. */
  getController(name: string): Controller<any> {
    const controller = this.controllers.get(name);
    if (!controller) {
      throw new Error(`Unknown controller: ${name}`);
    }
    return controller;
  }

  /** Type-safe convenience getter. */
  getControllerT<T extends Controller<any>>(name: string): T {
    return this.getController(name) as T;
  }

  /** Returns true if a controller with the given name is registered. */
  hasController(name: string): boolean {
    return this.controllers.has(name);
  }

  /** List all registered controller names (insertion order). */
  listControllers(): string[] {
    return Array.from(this.controllers.keys());
  }

  /** Clear all registered controllers (useful in tests). */
  reset(): void {
    this.controllers.clear();
  }
}

// =====================================================================
// 7. initControllers() — idempotent bootstrap
// =====================================================================

let _initialized = false;

/**
 * Create and wire up all controllers and their handles.
 * Safe to call multiple times — the first call does the work,
 * subsequent calls are no-ops.
 */
export function initControllers(): void {
  if (_initialized) return;

  const reg = ControllerRegistry.getInstance();

  // --- Instantiate controllers ---------------------------------------
  const searchController = new SearchController();

  // --- Register controllers with the registry -------------------------
  reg.registerController("search", searchController);

  // --- Register handles with each controller --------------------------
  registerSearchHandles(searchController);

  _initialized = true;
}

/** Helper: register all handles for the search domain. */
function registerSearchHandles(ctrl: SearchController): void {
  ctrl.register(new SemanticSearchHandle());
  ctrl.register(new KeywordSearchHandle());
  ctrl.register(new HybridSearchHandle());
}

/**
 * Tear down all controllers and reset the init flag.
 * Intended for use in test suites between runs.
 */
export function resetControllers(): void {
  ControllerRegistry.getInstance().reset();
  _initialized = false;
}