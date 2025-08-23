from utils import *
from pla import *

def compress_image(image, block_height, block_width):
    bit_planes = get_bit_planes(image)
    num_planes = len(bit_planes)

    minimized_blocks_inset = read_minimized_pla_files(output_parent_dir="pla_output")
    minimized_blocks_offset = read_minimized_pla_files(output_parent_dir="pla_offset_output")

    compressed_data = {
        "height": image.shape[0],
        "width": image.shape[1],
        "block_height": block_height,
        "block_width": block_width,
        "bit_planes": [],
    }

    # Process each bit plane
    for plane_index in range(num_planes):
        print('-------------------------------------------------------')
        print(f'For plane {plane_index}')
        print()
        all_black = 0
        all_white = 0
        compressible = 0
        incompressible = 0
        oneCube = 0
        twoCubes = 0
        threeCubes = 0
        onSet = 0
        offSet = 0
        oneIsolated = 0
        twoIsolated = 0
        threeIsolated = 0
        bit_plane = bit_planes[plane_index]
        blocks = split_bit_plane_into_blocks(bit_plane, block_height, block_width)
        plane_data = {"plane_index": plane_index, "blocks": []}

        for block_index, block in enumerate(blocks):
            block_data = {"block_index": block_index, "type": None, "data": []}

            num_ones = np.sum(block)
            if num_ones == 1:
                oneIsolated += 1
            elif num_ones == 2:
                twoIsolated += 1
            elif num_ones == 3:
                threeIsolated += 1

            if is_uniform_block(block):
                block_data["type"] = "uniform"
                block_data["data"] = [int(np.all(block == 1))]
                if block_data["data"][0] == 1:
                    all_white += 1
                else:
                    all_black += 1
            else:
                inset_cubes = minimized_blocks_inset.get(plane_index, {}).get(block_index, {}).get("cubes", [])
                offset_cubes = minimized_blocks_offset.get(plane_index, {}).get(block_index, {}).get("cubes", [])

                if inset_cubes and offset_cubes:
                    inset_code_allotment, inset_symbol = calculate_code_allotment(inset_cubes)
                    offset_code_allotment, offset_symbol = calculate_code_allotment(offset_cubes)

                    inset_encoded_bits, inset_cubes_len = encode_cubes(inset_cubes, inset_code_allotment)
                    offset_encoded_bits, offset_cubes_len = encode_cubes(offset_cubes, offset_code_allotment)

                    if len(inset_encoded_bits) <= len(offset_encoded_bits):
                        if inset_cubes_len == 1:
                            oneCube += 1
                        elif inset_cubes_len == 2 :
                            twoCubes += 1
                        elif inset_cubes_len == 3:
                            threeCubes += 1
                        selected_cubes = inset_cubes
                        selected_code_allotment = inset_code_allotment
                        selected_symbol = inset_symbol
                        selected_encoded_bits = inset_encoded_bits
                        selected_cubes_len = inset_cubes_len
                        offset_inset = 1
                    else:
                        if offset_cubes_len == 1:
                            oneCube += 1
                        elif offset_cubes_len == 2 :
                            twoCubes += 1
                        elif offset_cubes_len == 3:
                            threeCubes += 1
                        selected_cubes = offset_cubes
                        selected_code_allotment = offset_code_allotment
                        selected_symbol = offset_symbol
                        selected_encoded_bits = offset_encoded_bits
                        selected_cubes_len = offset_cubes_len
                        offset_inset = 0

                    if selected_cubes_len >= 5:
                        block_data["type"] = "incompressible"
                        incompressible += 1
                        block_data["data"] = block.flatten().tolist()
                    else:
                        block_data["type"] = "compressible"
                        compressible += 1
                        if offset_inset == 1:
                            onSet += 1
                        elif offset_inset ==0:
                            offSet += 1
                        block_data["data"] = {
                            "code_allotment": selected_code_allotment,
                            "code_allotment_bits": selected_symbol,
                            "number_of_cubes": selected_cubes_len,
                            "number_of_cubes_bin": format(selected_cubes_len, "03b"),
                            "encoded_bits": selected_encoded_bits,
                            "offset_inset": offset_inset,
                        }
                else:
                    block_data["type"] = "incompressible"
                    incompressible += 1
                    block_data["data"] = block.flatten().tolist()

            plane_data["blocks"].append(block_data)
        print('All black: ', all_black)
        print('All white: ', all_white)
        print('Compressible: ', compressible)
        print('Incompressible: ', incompressible)
        print('One cube:', oneCube)
        print('Two cubes:', twoCubes)
        print('Three cubes:', threeCubes)
        print('OnSet blocks:', onSet)
        print('OffSet blocks:', offSet)
        print('One Isolated:', oneIsolated)
        print('Two Isolated:', twoIsolated)
        print('Three Isolated:', threeIsolated)
        print()
        
        total_blocks = all_black + all_white + compressible + incompressible
        print('Percentage all black:', all_black*100/total_blocks)
        print('Percentage all white:', all_white*100/total_blocks)
        print('Percentage compressible:', compressible*100/total_blocks)
        print('Percentage incompressible:', incompressible*100/total_blocks)
        print('Percentage One cube:', oneCube*100/total_blocks)
        print('Percentage Two cubes:', twoCubes*100/total_blocks)
        print('Percentage Three cubes:', threeCubes*100/total_blocks)
        print('Percentage OnSet Blocks:', onSet*100/total_blocks)
        print("Percentage OffSet Blocks:", offSet*100/total_blocks)
        print('Percentage One Isolated:', oneIsolated*100/total_blocks)
        print('Percentage Two Isolated:', twoIsolated*100/total_blocks)
        print('Percentage Three Isolated:', threeIsolated*100/total_blocks)
        print('-------------------------------------------------------')




        compressed_data["bit_planes"].append(plane_data)

    return compressed_data

def decompress(compressed_bit_stream, block_height=4, block_width=8):
    decompressed_stream = []
    for index, i in enumerate(compressed_bit_stream):
        if i[:2] == [0, 1] or i[:2] == [0, 0]:
            if i[:2] == [0, 1]:
                decompressed_stream.append([1 for _ in range(block_height * block_width)])
            else:
                decompressed_stream.append([0 for _ in range(block_height * block_width)])
        elif i[:2] == [1, 1]:
            bits = [x for x in i[2:]]
            decompressed_stream.append(bits)
        elif i[:2] == [1, 0]:
            offset_inset = i[2]
            bits = [str(x) for x in i[3:]]
            if bits[0] == "0":
                allotment = calculate_decode_allotment("0")
                bits = bits[1:]
            elif bits[1] == "0":
                allotment = calculate_decode_allotment("10")
                bits = bits[2:]
            else:
                allotment = calculate_decode_allotment("11")
                bits = bits[2:]
            number_of_cubes = int("".join(bits[:3]), 2)
            bits = bits[3:]
            decoded = decode_cubes(bits, allotment)
            original_block_bits = [int(i) for i in deminimize_cubes(decoded)]
            if offset_inset == 0:
                original_block_bits = [1 - bit for bit in original_block_bits]  # Revert offset
            reordered_bits = revert_zigzag(original_block_bits, block_width, block_height)
            decompressed_stream.append(reordered_bits)
    return np.array(decompressed_stream)

def reconstruct_bit_planes(blocks, num_bit_planes=8, num_blocks_x=32, num_blocks_y=64, block_height=4, block_width=8, image_width=256,image_height=256):
    blocks = blocks.reshape(num_bit_planes, num_blocks_x * num_blocks_y, -1)

    return (
        blocks.reshape(
            num_bit_planes, num_blocks_y, num_blocks_x, block_height, block_width
        )
        .transpose(0, 1, 3, 2, 4)
        .reshape(num_bit_planes, image_height, image_width)
    )


def reconstruct_image(data, num_bit_planes=8, num_blocks_x=32, num_blocks_y=64, block_height=4, block_width=8, image_width=256,image_height=256):
    bit_planes = reconstruct_bit_planes(data, num_bit_planes=num_bit_planes, num_blocks_x=num_blocks_x, num_blocks_y=num_blocks_y, block_height=block_height, block_width=block_width, image_width=image_width,image_height=image_height)

    # Reconstructing image from bit planes
    bit_planes_uint8 = bit_planes.astype(np.uint8)
    reconstructed_image = bit_planes_uint8[0]

    # Using bitwise shift operations to reconstruct the image
    for i in range(1, len(bit_planes_uint8)):
        reconstructed_image |= bit_planes_uint8[i] << i

    return reconstructed_image

def json_to_arr(compressed_data):
    bit_planes = compressed_data["bit_planes"]
    compressed_bit_stream = []
    for plane in bit_planes:
        for block in plane["blocks"]:
            bit_stream = []
            block_type = block["type"]
            if block_type == "uniform":
                if block["data"] == [1]:
                    bit_stream += [0, 1]
                else:
                    bit_stream += [0, 0]
                compressed_bit_stream.append(bit_stream)
                continue
            elif block_type == "incompressible":
                bit_stream += [1, 1]
                bit_stream += block["data"]
                compressed_bit_stream.append(bit_stream)
                continue
            else:
                bit_stream += [1, 0]
                offset_inset = block["data"]["offset_inset"]
                bit_stream += [offset_inset]
                data = block["data"]
                bit_stream += [int(i) for i in data["code_allotment_bits"]]
                bit_stream += [int(i) for i in data["number_of_cubes_bin"]]
                bit_stream += [int(i) for i in data["encoded_bits"]]
                compressed_bit_stream.append(bit_stream)
                continue
    return compressed_bit_stream


