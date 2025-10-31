import sys


def cube_intersect(c1, c2):
    """Check if two cubes intersect and return intersection"""
    result = []
    for ch1, ch2 in zip(c1, c2):
        if ch1 == '-' and ch2 == '-':
            result.append('-')
        elif ch1 == '-':
            result.append(ch2)
        elif ch2 == '-':
            result.append(ch1)
        elif ch1 == ch2:
            result.append(ch1)
        else:
            return None
    return ''.join(result)


def cube_subset(c1, c2):
    """Check if cube c1 is a subset of cube c2"""
    for ch1, ch2 in zip(c1, c2):
        if ch2 == '-':
            continue
        elif ch1 == '-':
            return False
        elif ch1 != ch2:
            return False
    return True


def sharp_single(c1, c2):
    """Compute c1 # c2 (c1 minus c2)"""
    intersection = cube_intersect(c1, c2)

    if intersection is None:
        return [c1]

    if cube_subset(c1, c2):
        return []

    results = []
    for i, (ch1, ch2) in enumerate(zip(c1, c2)):
        if ch1 == '-' and ch2 != '-':
            result_cube = list(c1)
            if ch2 == '0':
                result_cube[i] = '1'
            else:
                result_cube[i] = '0'
            results.append(''.join(result_cube))

    return results


def sharp_operation(c1, cubes2):
    """Compute c1 # (all cubes in cubes2)"""
    current = [c1]

    for c2 in cubes2:
        next_cubes = []
        for cube in current:
            result = sharp_single(cube, c2)
            next_cubes.extend(result)
        current = next_cubes
        if not current:
            break

    return current


def process_blocks(block1, block2):
    """Process two blocks and compute block1 # block2"""
    cubes1 = [cube[0] for cube in block1['cubes']]
    cubes2 = [cube[0] for cube in block2['cubes']]

    all_results = []
    for c1 in cubes1:
        result_cubes = sharp_operation(c1, cubes2)
        all_results.extend(result_cubes)

    return all_results


if __name__ == "__main__":
    pass
