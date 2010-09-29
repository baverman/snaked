def append_attr(obj, attr, value):
    """
    Appends value to object attribute
    
    Attribute may be undefined
    
    For example:
        append_attr(obj, 'test', 1)
        append_attr(obj, 'test', 2)
        
        assert obj.test == [1, 2]
    """
    try:
        getattr(obj, attr).append(value)
    except AttributeError:
        setattr(obj, attr, [value])
