from ..buildcalculator import ItemSet


def get_participant_item_events(match, participant):
    events = []
    for frame in match.frames:
        for event in sorted(frame, key=lambda event: (event.timestamp, event.type.value)):
            if event.participant is participant and \
            (event.item is not None or event.item_after is not None or event.item_before is not None) and \
            (event.item is None or (event.item.name != 'Health Potion' and event.item.name != 'Total Biscuit of Rejuvenation')):
                events.append(event)
    return events


def process_item_events(events):
    items = ItemSet()
    for i, event in enumerate(events):
        #print([item.name for item in items.list], event.type, str(event.item))
        if event.type.value == 'ITEM_PURCHASED':
            items.add(event.item)
        elif event.type.value == 'ITEM_DESTROYED':
            items.remove(event.item)
        elif event.type.value == 'ITEM_SOLD':
            items.remove(event.item)
        elif event.type.value == 'ITEM_UNDO':
            if events[i-1].type.value == 'ITEM_PURCHASED':
                items.remove(events[i-1].item)
            elif events[i-1].type.value == 'ITEM_DESTROYED':
                items.add(events[i-1].item)
            elif events[i-1].type.value == 'ITEM_SOLD':
                items.add(events[i-1].item)
    return items

