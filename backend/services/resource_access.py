from __future__ import annotations

from sqlalchemy.orm import Session

from core.exceptions import AuthError, BusinessError
from core.error_codes import ErrorCode
from models.agent_config import AgentConfig
from models.agent_role_share import AgentRoleShare
from models.db_connection import DbConnection
from models.datasource_role_share import DatasourceRoleShare
from models.file_upload import FileUpload
from models.role_agent import RoleAgent
from models.role_datasource import RoleDatasource
from models.user import User

PERM_ORDER = {"use": 1, "edit": 2, "admin": 3}


def is_admin(user: User) -> bool:
    return bool(user.role and user.role.code == "admin")


def _max_permission(perms: list[str | None]) -> str | None:
    valid = [p for p in perms if p in PERM_ORDER]
    if not valid:
        return None
    return max(valid, key=lambda p: PERM_ORDER[p])


def get_agent_permission(db: Session, user: User, agent: AgentConfig) -> str | None:
    if is_admin(user):
        return "admin"
    perms: list[str | None] = []
    if agent.created_by == user.id:
        perms.append("admin")
    if user.role_id:
        grant = db.query(RoleAgent).filter(
            RoleAgent.role_id == user.role_id,
            RoleAgent.agent_id == agent.id,
        ).first()
        if grant:
            perms.append(grant.permission)
        share = db.query(AgentRoleShare).filter(
            AgentRoleShare.role_id == user.role_id,
            AgentRoleShare.agent_id == agent.id,
        ).first()
        if share:
            perms.append(share.permission)
    if agent.visibility == "public":
        perms.append("use")
    return _max_permission(perms)


def list_visible_agents(db: Session, user: User, *, active_only: bool = True) -> list[AgentConfig]:
    query = db.query(AgentConfig)
    if active_only:
        query = query.filter(AgentConfig.is_active == 1)
    agents = query.order_by(AgentConfig.id).all()
    visible: list[AgentConfig] = []
    for agent in agents:
        if get_agent_permission(db, user, agent):
            visible.append(agent)
    return visible


def require_agent_permission(
    db: Session, user: User, agent_id: int, min_permission: str = "use",
) -> AgentConfig:
    agent = db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()
    if not agent:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="智能体不存在")
    perm = get_agent_permission(db, user, agent)
    if not perm or PERM_ORDER[perm] < PERM_ORDER[min_permission]:
        raise AuthError(code=ErrorCode.INSUFFICIENT_PERMISSION, message="无权访问该智能体")
    return agent


def _datasource_record(db: Session, resource_type: str, resource_id: int):
    if resource_type == "db_connection":
        return db.query(DbConnection).filter(DbConnection.id == resource_id).first()
    if resource_type == "file_upload":
        return db.query(FileUpload).filter(FileUpload.id == resource_id).first()
    return None


def get_datasource_permission(
    db: Session, user: User, resource_type: str, resource_id: int,
) -> str | None:
    record = _datasource_record(db, resource_type, resource_id)
    if not record:
        return None
    if is_admin(user):
        return "admin"
    perms: list[str | None] = []
    if record.created_by == user.id:
        perms.append("admin")
    if user.role_id:
        grant = db.query(RoleDatasource).filter(
            RoleDatasource.role_id == user.role_id,
            RoleDatasource.resource_type == resource_type,
            RoleDatasource.resource_id == resource_id,
        ).first()
        if grant:
            perms.append(grant.permission)
        share = db.query(DatasourceRoleShare).filter(
            DatasourceRoleShare.role_id == user.role_id,
            DatasourceRoleShare.resource_type == resource_type,
            DatasourceRoleShare.resource_id == resource_id,
        ).first()
        if share:
            perms.append(share.permission)
    if record.visibility == "public":
        perms.append("use")
    return _max_permission(perms)


def list_visible_db_connections(db: Session, user: User) -> list[DbConnection]:
    connections = db.query(DbConnection).filter(DbConnection.is_active == 1).order_by(DbConnection.id).all()
    return [c for c in connections if get_datasource_permission(db, user, "db_connection", c.id)]


def list_visible_file_uploads(db: Session, user: User) -> list[FileUpload]:
    uploads = db.query(FileUpload).order_by(FileUpload.updated_at.desc()).all()
    return [u for u in uploads if get_datasource_permission(db, user, "file_upload", u.id)]


def require_datasource_permission(
    db: Session, user: User, resource_type: str, resource_id: int, min_permission: str = "use",
):
    record = _datasource_record(db, resource_type, resource_id)
    if not record:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="数据源不存在")
    perm = get_datasource_permission(db, user, resource_type, resource_id)
    if not perm or PERM_ORDER[perm] < PERM_ORDER[min_permission]:
        raise AuthError(code=ErrorCode.INSUFFICIENT_PERMISSION, message="无权访问该数据源")
    return record


def set_agent_role_shares(db: Session, agent_id: int, role_ids: list[int], permission: str = "use"):
    db.query(AgentRoleShare).filter(AgentRoleShare.agent_id == agent_id).delete()
    for role_id in role_ids:
        db.add(AgentRoleShare(agent_id=agent_id, role_id=role_id, permission=permission))


def get_agent_shared_role_ids(db: Session, agent_id: int) -> list[int]:
    rows = db.query(AgentRoleShare.role_id).filter(AgentRoleShare.agent_id == agent_id).all()
    return [r[0] for r in rows]


def set_datasource_role_shares(
    db: Session, resource_type: str, resource_id: int, role_ids: list[int], permission: str = "use",
):
    db.query(DatasourceRoleShare).filter(
        DatasourceRoleShare.resource_type == resource_type,
        DatasourceRoleShare.resource_id == resource_id,
    ).delete()
    for role_id in role_ids:
        db.add(DatasourceRoleShare(
            resource_type=resource_type,
            resource_id=resource_id,
            role_id=role_id,
            permission=permission,
        ))


def get_datasource_shared_role_ids(db: Session, resource_type: str, resource_id: int) -> list[int]:
    rows = db.query(DatasourceRoleShare.role_id).filter(
        DatasourceRoleShare.resource_type == resource_type,
        DatasourceRoleShare.resource_id == resource_id,
    ).all()
    return [r[0] for r in rows]
