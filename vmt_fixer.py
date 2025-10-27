"""
Simple VMT fixer - converts CS:GO materials to Momentum Mod compatible
"""

import re
from pathlib import Path

def fix_vmt(vmt_content, material_name):
    """Convert CS:GO VMT to VertexLitGeneric with proper paths"""
    # Extract original paths
    basetexture_match = re.search(r'"?\$basetexture"?\s+"([^"]+)"', vmt_content, re.IGNORECASE)
    bumpmap_match = re.search(r'"?\$bumpmap"?\s+"([^"]+)"', vmt_content, re.IGNORECASE)
    
    # TODO: Texture paths 
    if 'glove_sporty' in material_name:
        if '_left' in material_name or '_right' in material_name:
            basetexture = "models/weapons/v_models/arms/glove_sporty/glove_sporty"
        else:
            basetexture = "models/weapons/v_models/arms/glove_sporty/glove_sporty"
        bumpmap = "models/weapons/v_models/arms/glove_sporty/glove_sporty_normal"
        
    elif 'bare_arm' in material_name:
        basetexture = f"models/weapons/v_models/arms/bare/{material_name}"
        bumpmap = f"models/weapons/v_models/arms/bare/{material_name}_normal"
        
    elif 'knife_' in material_name:
        basetexture = f"models/weapons/v_models/knife_m9_bay/{material_name}"
        bumpmap = f"models/weapons/v_models/knife_m9_bay/{material_name}_normal"
        
    else:
        # Fallback
        basetexture = basetexture_match.group(1) if basetexture_match else material_name
        bumpmap = bumpmap_match.group(1) if bumpmap_match else f"{basetexture}_normal"

    return f'''VertexLitGeneric
{{
\t"$basetexture" "{basetexture}"
\t"$bumpmap" "{bumpmap}"
\t"$phong" "1"
\t"$phongboost" "1"
\t"$phongexponent" "20"
\t"$phongfresnelranges" "[1 1 1]"
}}'''

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
        
        for vmt_file in vmt_files:
            try:
                original = vmt_file.read_text(encoding='utf-8')
                fixed = fix_vmt(original, material)
                rel_path = vmt_file.relative_to(csgo_materials_dir)
                output_file = output_dir / rel_path
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(fixed, encoding='utf-8')
                
                print(f"[vmt_fixer] Fixed: {material}")
                
            except Exception as e:
                print(f"[vmt_fixer] Error fixing {material}: {e}")