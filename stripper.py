import os

def strip_base_files(file_dir, src_dir, subpaths, to_remove, to_keep, subsection):
    """There's a bunch of base game files that are necessary but contain _some_ hardcoded references to provinces.
    Rather than having to manually remove them, let's try to do it automatically.
    
    Currently known to work with the following subpaths:
    - 
    and suspected to work with:
    - common/travel/point_of_interest_types/travel_point_of_interest_types.txt  # TODO: add poi_grand_city for the central cities.
    """
    expanded_subpaths = []
    while len(subpaths) > 0:
        subpath = subpaths.pop()
        if os.path.isdir(os.path.join(src_dir, subpath)):
            subpaths.extend([os.path.join(src_dir, subpath, more) for more in os.listdir(os.path.join(src_dir, subpath))])
        else:
            expanded_subpaths.append(subpath)

    for subpath in expanded_subpaths:
        file_stripped = False
        file_buffer = ""
        with open(os.path.join(src_dir, subpath), encoding='utf_8_sig') as inf:
            valid = True
            brackets = 0
            mod_brackets = 0
            mod = False
            buffer = ""
            mod_buffer = ""
            for line in inf:
                brackets += line.count("{")
                if brackets > 0 and (any([tr in line for tr in to_remove])) and (not(any([tk in line for tk in to_keep]))):
                    valid = False
                    file_stripped = True
                if subsection is not None and brackets > 0 and valid and any([ss in line for ss in subsection]):
                    mod = True
                    mod_brackets = brackets - 1  # This is when it closes
                if mod:
                    mod_buffer += line
                elif valid:
                    buffer += line
                brackets -= line.count("}")
                if mod and brackets == mod_brackets:
                    if valid:
                        buffer += mod_buffer
                        mod_buffer = ""
                    else:
                        valid = True
                        mod_buffer = ""
                    mod = False
                if brackets == 0:
                    if valid and mod:
                        print(f"There's an issue with parsing {subpath}")
                    elif valid:
                        file_buffer = file_buffer + buffer
                    buffer = ""
                    valid = True
        if file_stripped:  # We did a replacement, so need to write out buffer.
            relpath = os.path.relpath(subpath,src_dir)
            print(relpath)
            os.makedirs(os.path.join(file_dir, os.path.dirname(relpath)), exist_ok=True)
            with open(os.path.join(file_dir, relpath), 'w', encoding='utf_8_sig') as outf:
                outf.write(file_buffer)