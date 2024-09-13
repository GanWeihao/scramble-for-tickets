def time_delta(begin_time, end_time, type='hour'):
    delta = end_time - begin_time

    if type == 'hour':
        return delta.seconds // 3600
    elif type == 'minute':
        return delta.seconds // 60 % 60
    elif type == 'second':
        return delta.seconds % 60
    elif type == 'day':
        return delta.days
    else:
        raise ValueError('Unknown time type')

