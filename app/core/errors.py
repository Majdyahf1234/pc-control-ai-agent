class AgentError(Exception):
    pass

class PermissionError(AgentError):
    pass

class PlannerError(AgentError):
    pass

class ExecutionStopped(AgentError):
    pass
