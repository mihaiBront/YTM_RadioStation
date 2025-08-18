import os
import json
from typing import Any, Optional, get_origin, get_args
import logging as log
from dataclasses import dataclass, field, fields

from lib.FileManagement import FileManagement

class Serializable(FileManagement):
    """
    Abstract class for classes that have to be serializable. Includes methods for working with
    text JSONs, as well as some extra comodity methods for excluding private elements from 
    those JSON strings, passing a reference to the possible outer class of an inner one, and a
    config dialog (most of the abstract methods comming empty)
    """

    def exclude_private(self) -> dict:
        """
        Excludes private properties from dictionary for JSON serialization

        :return: (dict) Filtered dictionary
        """
        no_private: dict = self.__dict__.copy()
        keys_to_pop = list([key for key, val in self.__dict__.items() if key[0] == "_"])
        for key in keys_to_pop:
            no_private.pop(key)
        return no_private

    @classmethod    # FIXME: should be private but have to fix class parity in InspectionLibEfi first
    def from_dict(cls, self: Any) -> Optional[object]:
        """
        Helper class for deserializing JSONs. Supports primitives, nested Serializable,
        dict passthrough, and lists of either.

        Args:
            self (Any): Source mapping (typically a dict) to build the object from

        Returns:
            object: Instance of the current class populated from the mapping
        """

        field_types = {f.name: f.type for f in fields(cls)}
        kwargs = {}
        for field_name, field_type in field_types.items():
            value = self.get(field_name) if isinstance(self, dict) else getattr(self, field_name, None)

            # If the value is missing, try to construct a default; fallback to None
            if value is None:
                try:
                    kwargs[field_name] = field_type()
                except Exception:
                    kwargs[field_name] = None
                continue

            origin = get_origin(field_type)
            args = get_args(field_type)

            # Handle list[...] or plain list
            if origin is list or field_type is list:
                inner_type = args[0] if args else None
                if isinstance(value, list):
                    if inner_type and hasattr(inner_type, "from_dict"):
                        kwargs[field_name] = [inner_type.from_dict(item) for item in value]
                    else:
                        # passthrough list (e.g., list[dict] or list of primitives)
                        kwargs[field_name] = value
                else:
                    kwargs[field_name] = []
                continue

            # Handle dict[K, V] or plain dict
            if origin is dict or field_type is dict:
                if isinstance(value, dict):
                    kwargs[field_name] = value
                else:
                    kwargs[field_name] = {}
                continue

            # If value is a dict and field_type looks like a Serializable
            if isinstance(value, dict) and hasattr(field_type, "from_dict"):
                kwargs[field_name] = field_type.from_dict(value)
                continue

            # Primitive or passthrough
            try:
                kwargs[field_name] = field_type(value)
            except Exception:
                kwargs[field_name] = value

        return cls(**kwargs)
         
    @classmethod
    def deserialize(cls, json_string: str) -> object:
        """
        Deserializes JSON string to object according to the cls.from_dict method

        Args:
            json_string (str): Serialized object
        
        Returns:
            object: Object from json
        """

        _obj: type(cls) = cls.from_dict(json.loads(json_string)) # type: ignore
        return _obj

    def serialize(self) -> str:
        """
        Serializes object in a JSON format (excluding private parameters)

        Returns:
            str: Serialized object
        """
        return json.dumps(self, default=lambda o: o.exclude_private(), sort_keys=False, indent=4)

    @classmethod
    def from_file(cls, json_file_path: str):
        """
        Gets JSON from file, and deserializes it to current object class
        
        Args:
            json_file_path (str): Res to JSON file
        
        Returns:
            (object): Deserialized from JSON
        """
        try:
            with open(cls.path_to_python(json_file_path)) as file:
                json_string = file.read()
        except Exception as ex:
            log.error(f"Couldn't open or read '{json_file_path}' ({ex}). Aborted")
            return None

        if json_string is None:
            log.error("Text from file is None. Aborted")
            return None

        json_obj = None

        try:
            json_obj = cls.deserialize(json_string)
        except Exception as ex:
            log.warning(f"Failed getting object from '{json_file_path}' ({ex})")

        if json_obj is None:
            log.error("Unable to deserialize json (is none)")
            return None

        log.info("Deserialized object correctly")
        return json_obj

    @classmethod
    def to_recursive_list(cls):
        field_types = {f.name: f.type for f in fields(cls)}
        kwargs = {}
        
        md_lst = []
        
        for item_name, item_type in field_types.items():
            if item_name[0] != "_":
                item_type_full = str(item_type)
                item_type_name = item_type.__name__
                
                md_lst.append(f"- `({item_type_name}) {item_name}`: >> Description")
                
                if "." in item_type_full[1:-1]:
                    inners = item_type.to_recursive_list()
                    for inner in inners:
                        md_lst.append(f"\t{inner}")
        
        return md_lst
    
    def to_file(self, file_path: str):
        """
        Saves an object onto a specified file

        :param file_path: (str) Res to file where to save the object, serialized as json
        :return: (str) Returns file_path back
        """

        file_path = self.path_to_python(file_path)

        # check if a file extension was specified
        if "." not in file_path:
            log.warning("The path specified has no file extension. File not saved")
            return None

        # check if path to dir existed
        dir_path = file_path[:file_path.rfind("/")]

        if not os.path.exists(dir_path):
            log.info(f"Dir didn't exist. Created '{dir_path}'")
            os.mkdir(dir_path)

        with open(file_path, "w") as file:
            file.write(self.serialize())
            log.info("Object successfully saved on file")

        return file_path

    def to_dict(self) -> dict:
        """
        Convert a dataclass instance to a dictionary.
        Handles basic Python types and nested Serializable objects.
        
        Returns:
            Dictionary representation of the dataclass instance
        """
        result = {}
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, Serializable):
                result[field_name] = field_value.to_dict()
            elif isinstance(field_value, (list, tuple)):
                result[field_name] = [
                    item.to_dict() if isinstance(item, Serializable) else item 
                    for item in field_value
                ]
            else:
                result[field_name] = field_value
        return result
