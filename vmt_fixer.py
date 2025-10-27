"""
skin2momentum
vmt_fixer - converts CS:GO materials to Momentum Mod compatible
"""

import re
from pathlib import Path

def fix_vmt(vmt_content, material_name, material_rel_path, csgo_materials_dir):
    """Convert CS:GO VMT to VertexLitGeneric with proper paths"""

    # Extract original paths from VMT
    basetexture_match = re.search(r'"?\$basetexture"?\s+"([^"]+)"', vmt_content, re.IGNORECASE)
    bumpmap_match = re.search(r'"?\$bumpmap"?\s+"([^"]+)"', vmt_content, re.IGNORECASE)
    material_dir = str(material_rel_path.parent).replace('\\', '/')
    material_folder = csgo_materials_dir / material_rel_path.parent
    
    # Handle basetexture
    if basetexture_match:
        original_basetexture = basetexture_match.group(1).strip()

        # Handle special CS:GO cases
        if original_basetexture.lower() == "black":
            # For gloves that use "black" use the base glove texture
            base_name = material_name.split('_')[0] + '_' + material_name.split('_')[1]
            base_texture_file = material_folder / f"{base_name}.vtf"
            if base_texture_file.exists():
                basetexture = f"{material_dir}/{base_name}"
            else:
                # Try _color suffix if no base texture
                color_texture_file = material_folder / f"{base_name}_color.vtf"
                if color_texture_file.exists():
                    basetexture = f"{material_dir}/{base_name}_color"
                else:
                    # Fallback to material name if base doesnt exist
                    texture_file = material_folder / f"{material_name}.vtf"
                    if texture_file.exists():
                        basetexture = f"{material_dir}/{material_name}"
                    else:
                        basetexture = f"{material_dir}/{base_name}"
        elif '/' in original_basetexture and original_basetexture.startswith('models/'):
            # Use original path if its a full path
            basetexture = original_basetexture
        else:
            # Check if the materials own texture file exists
            texture_file = material_folder / f"{material_name}.vtf"
            if texture_file.exists():
                basetexture = f"{material_dir}/{material_name}"
            else:
                # Try base name
                base_name = material_name.split('_')[0] + '_' + material_name.split('_')[1]
                base_texture_file = material_folder / f"{base_name}.vtf"
                if base_texture_file.exists():
                    basetexture = f"{material_dir}/{base_name}"
                else:
                    # Try with _color suffix for gloves
                    color_texture_file = material_folder / f"{base_name}_color.vtf"
                    if color_texture_file.exists():
                        basetexture = f"{material_dir}/{base_name}_color"
                    else:
                        basetexture = f"{material_dir}/{material_name}"

    else:
        # No basetexture found, try to find appropriate texture
        texture_file = material_folder / f"{material_name}.vtf"
        if texture_file.exists():
            basetexture = f"{material_dir}/{material_name}"
        else:
            # Try base name
            base_name = material_name.split('_')[0] + '_' + material_name.split('_')[1]
            base_texture_file = material_folder / f"{base_name}.vtf"
            if base_texture_file.exists():
                basetexture = f"{material_dir}/{base_name}"
            else:
                # Try with _color suffix
                color_texture_file = material_folder / f"{base_name}_color.vtf"
                if color_texture_file.exists():
                    basetexture = f"{material_dir}/{base_name}_color"
                else:
                    basetexture = f"{material_dir}/{material_name}"
    
    # Handle bumpmap
    bumpmap = None
    if bumpmap_match:
        original_bumpmap = bumpmap_match.group(1).strip()
        if '/' in original_bumpmap and original_bumpmap.startswith('models/'):
            # Check if the referenced texture exists
            bumpmap_rel_path = original_bumpmap.replace('models/', '') + '.vtf'
            bumpmap_file = csgo_materials_dir / 'models' / bumpmap_rel_path.replace('models/', '')
            if bumpmap_file.exists():
                bumpmap = original_bumpmap
        else:
            # Try to find normal map in same directory
            normal_file = material_folder / f"{original_bumpmap}.vtf"
            if normal_file.exists():
                bumpmap = f"{material_dir}/{original_bumpmap}"
    
    # If no bumpmap found from VMT, try common patterns
    if not bumpmap:
        normal_variants = [
            f"{material_name}_normal",
            f"{material_name.split('_')[0]}_{material_name.split('_')[1]}_normal" if "_" in material_name else None
        ]
        for variant in normal_variants:
            if variant:
                normal_file = material_folder / f"{variant}.vtf"
                if normal_file.exists():
                    bumpmap = f"{material_dir}/{variant}"
                    break
    
    # Build VMT content
    vmt_lines = ['VertexLitGeneric', '{']
    vmt_lines.append(f'\t"$basetexture" "{basetexture}"')
    
    if bumpmap:
        vmt_lines.append(f'\t"$bumpmap" "{bumpmap}"')
    
    vmt_lines.extend([
        '\t"$phong" "1"',
        '\t"$phongboost" "1"',
        '\t"$phongexponent" "20"',
        '\t"$phongfresnelranges" "[1 1 1]"',
        '}'
    ])
    
    return '\n'.join(vmt_lines)

def find_materials_from_smd(smd_file):
    """Find material names in SMD file"""
    try:
        content = smd_file.read_text(encoding='utf-8', errors='ignore')
        materials = []
        in_triangles = False
        
        for line in content.splitlines():
            line = line.strip()
            if line == 'triangles':
                in_triangles = True
            elif line == 'end':
                in_triangles = False
            elif in_triangles and line and not re.match(r'^[\d\.\-\s]+$', line) and len(line.split()) == 1:
                if line not in materials:
                    materials.append(line)
        return materials
    except:
        return []

def process_materials(csgo_materials_dir, output_dir, material_names):
    """Process and fix VMTs"""
    print(f"[vmt_fixer] Processing {len(material_names)} materials")
    
    for material in material_names:
        # Find VMT file
        vmt_files = list(csgo_materials_dir.rglob(f"{material}.vmt"))
        
        if not vmt_files:
            print(f"[vmt_fixer] VMT not found for {material}")
            continue
            
        for vmt_file in vmt_files:
            try:
                original = vmt_file.read_text(encoding='utf-8')
                rel_path = vmt_file.relative_to(csgo_materials_dir)
                fixed = fix_vmt(original, material, rel_path, csgo_materials_dir)
                
                output_file = output_dir / rel_path
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(fixed, encoding='utf-8')
                
                print(f"[vmt_fixer] Fixed: {material} -> {rel_path}")
                
            except Exception as e:
                print(f"[vmt_fixer] Error fixing {material}: {e}")

def get_cdmaterials_paths(csgo_materials_dir, material_names):
    """Generate $cdmaterials paths for QC based on actual material locations"""
    paths = set()
    
    for material in material_names:
        vmt_files = list(csgo_materials_dir.rglob(f"{material}.vmt"))
        
        for vmt_file in vmt_files:
            rel_path = vmt_file.relative_to(csgo_materials_dir)
            dir_path = str(rel_path.parent).replace('\\', '/')
            if dir_path and dir_path != '.':
                paths.add(f'"{dir_path}/"')
    
    # Add common fallback paths
    paths.add('"models/weapons/"')
    paths.add('""')
    
    return sorted(paths)