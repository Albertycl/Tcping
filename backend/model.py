import datetime
# from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.sqltypes import TIMESTAMP
db = SQLAlchemy()


class b11_huck_ge_probes(db.Model):
    __tablename__ = "b11_huck_ge_probes"
    id = db.Column(db.Integer, primary_key=True)
    # Map python attribute 'ge_server_private_ip' to DB column 'server_private_ip'
    ge_server_private_ip = db.Column("server_private_ip", db.String(255))
    isp_expected = db.Column(db.String(255))
    # Map python attribute 'ge_city' to DB column 'city'
    ge_city = db.Column("city", db.String(255))
    public_ip = db.Column(db.String(255))
    isp = db.Column(db.String(255))
    hostname = db.Column(db.String(255))

    @property
    def serialize(self):
        return {
            "id": self.id,
            "isp_expected": self.isp_expected,
            "ge_server_private_ip": self.ge_server_private_ip,
            "ge_city": self.ge_city,
            # Aliases for frontend compatibility
            "server_ip": self.ge_server_private_ip,
            "which_city": self.ge_city,
            "linux_public_ip": self.public_ip,
            "isp": self.isp,
            "hostname": self.hostname,
        }
        
        
        
class c10_for_paping_probes(db.Model):
    __tablename__ = "c10_for_paping_probes"
    id = db.Column(db.Integer, primary_key=True)
    server_ip = db.Column(db.String(255))
    which_isp = db.Column(db.String(255))
    which_city = db.Column(db.String(255))

    @property
    def serialize(self):
        return {
            "server_ip": self.server_ip,
            "which_isp": self.which_isp,
            "which_city": self.which_city,
        }

class WhitelistCondition(db.Model):
    __bind_key__ = 'whitelist_db'
    __tablename__ = "a97_whitelist_conditions"
    id = db.Column(db.Integer, primary_key=True)
    condition_type = db.Column(db.String(20))
    condition_pattern = db.Column(db.String(500))
    condition_name = db.Column(db.String(200))
    description = db.Column(db.String(500))
    is_enabled = db.Column(db.Boolean, default=True)
    is_built_in = db.Column(db.Boolean, default=False)
    country_specific = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    @property
    def serialize(self):
        return {
            "id": self.id,
            "condition_type": self.condition_type,
            "condition_pattern": self.condition_pattern,
            "condition_name": self.condition_name,
            "description": self.description,
            "is_enabled": self.is_enabled,
            "is_built_in": self.is_built_in,
            "country_specific": self.country_specific,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }