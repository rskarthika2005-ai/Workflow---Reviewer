from dataclasses import dataclass


@dataclass
class Requirement:
    req_id: str
    text: str                      
    route: str                     
    order: int                     
    version: str = "v1"
    location: str = ""             
    condition: dict | None = None  
    supported: bool = True        


@dataclass
class SpecRule:
    rule_id: str
    ref_id: str | None             
    condition: dict | None
    route: str
    order: int
    version: str = "v1"
    location: str = ""


@dataclass
class WorkflowNode:
    node_id: str
    condition: dict | None
    if_true: str                  
    if_false: str                  
    version: str = "v1"
    location: str = ""


@dataclass
class Snippet:
    snippet_id: str
    node_id: str
    code: str
    version: str = "v1"
    location: str = ""


@dataclass
class Approval:
    approval_id: str
    req_id: str                    
    field: str                    
    new_value: float             
    unit: str = "minutes"
    status: str = "proposed"       
    change_order: int = 1         
    applies_to_version: str = "v1" 
    version: str = "v1"
    location: str = ""