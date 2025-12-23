from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

class BaseModel(Base):
    """
    Base Model representing common fields for all SQLAlchemy models.
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ------------------------------------------------
    # Update helpers
    # ------------------------------------------------

    def update(self, data: dict, session=None, save=False):
        """
        Update model fields safely
        """
        allowed_fields = {column.name for column in self.__table__.columns}

        for key, value in data.items():
            if key in allowed_fields:
                setattr(self, key, value)

        if save and session:
            session.add(self)
            session.commit()

    def update_params(self, params: dict):
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # ------------------------------------------------
    # Query helpers
    # ------------------------------------------------

    @classmethod
    def get_by_id(cls, session, id):
        return session.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_or_create(cls, session, query: dict, defaults: dict):
        obj = session.query(cls).filter_by(**query).first()
        if obj:
            return obj, False
        else:
            obj = cls(**{**query, **defaults})
            session.add(obj)
            session.commit()
            return obj, True

    @classmethod
    def check_unique(cls, session, field, data, error_message, current_id=None):
        value = data.get(field)

        query = session.query(cls).filter(getattr(cls, field) == value)
        
        if current_id:
            query = query.filter(cls.id != current_id)

        if value and query.first():
            raise ValueError(error_message)

    # ------------------------------------------------
    # Filtering
    # ------------------------------------------------

    @staticmethod
    def get_filtered_query(query, fields, query_params):
        """
        fields = {
            "name": {"type": "TEXT"},
            "age": {"type": "INT"},
            "created_at": {"type": "DATE"}
        }
        """

        for name, config in fields.items():
            if name not in query_params:
                continue

            value = query_params.get(name)
            field_name = config.get("field", name)
            model_class = query.column_descriptions[0]['type']
            field = getattr(model_class, field_name)

            if config["type"] == "TEXT":
                query = query.filter(field.ilike(f"%{value}%"))

            elif config["type"] == "INT":
                query = query.filter(field == value)

            elif config["type"] == "BOOL":
                query = query.filter(field == value)

            elif config["type"] == "DATE":
                query = query.filter(func.date(field) == value)

        return query

    # ------------------------------------------------
    # Sorting
    # ------------------------------------------------

    @staticmethod
    def get_ordered_query(query, sortable_fields, order_by=None, descending=False):
        if not order_by or order_by not in sortable_fields:
            return query

        model_class = query.column_descriptions[0]['type']
        field_name = sortable_fields[order_by].get("field", order_by)
        field = getattr(model_class, field_name)

        if descending:
            query = query.order_by(field.desc())
        else:
            query = query.order_by(field.asc())

        return query

    # ------------------------------------------------
    # Pagination
    # ------------------------------------------------

    @staticmethod
    def get_paginated_query(query, page, page_size):
        try:
            page = int(page)
            page_size = int(page_size)
        except (TypeError, ValueError):
            return query

        if page <= 0 or page_size <= 0:
            return query

        start = (page - 1) * page_size
        
        return query.offset(start).limit(page_size)

    # ------------------------------------------------
    # Search
    # ------------------------------------------------

    @classmethod
    def search(cls, query, value, fields):
        model_class = query.column_descriptions[0]['type']
        
        search_conditions = []
        for field in fields:
            field_attr = getattr(model_class, field)
            search_conditions.append(field_attr.ilike(f"%{value}%"))

        from sqlalchemy import or_
        return query.filter(or_(*search_conditions))

    # ------------------------------------------------
    # Results builder (FILTER + SEARCH + SORT + PAGINATION)
    # ------------------------------------------------

    @classmethod
    def get_results(
        cls,
        session,
        query_params=None,
        query_param_fields=None,
        sortable_fields=None,
        searchable_cols=None
    ):
        query = session.query(cls)

        # Filtering
        if query_param_fields and query_params:
            query = cls.get_filtered_query(
                query,
                query_param_fields,
                query_params
            )

        # Search
        if (
            query_params
            and query_params.get("search")
            and searchable_cols
        ):
            query = cls.search(query, query_params["search"], searchable_cols)

        total_records = query.count()

        # Sorting
        query = cls.get_ordered_query(
            query,
            sortable_fields or {},
            query_params.get("sort_by") if query_params else None,
            query_params.get("desc") if query_params else None
        )

        # Pagination
        if query_params and query_params.get("paginate"):
            query = cls.get_paginated_query(
                query,
                query_params.get("page"),
                query_params.get("items")
            )

        return query.all(), total_records

    # ------------------------------------------------
    # Delete
    # ------------------------------------------------

    def delete(self, session):
        session.delete(self)
        session.commit()
