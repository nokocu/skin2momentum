"""
skin2momentum
"""

import os
import sys
import re
import shutil
import subprocess
import tempfile
import argparse
from pathlib import Path

class Converter:

    def __init__(self, args):
        """Init"""
        # Paths
        self.data_dir = Path(args.data).resolve()
        self.game_dir = Path(args.game).resolve()
        self.output_dir = Path(args.output).resolve() / "models" / "weapons"
        self.scripts_dir = Path(__file__).parent / "scripts"
        self.weapon_type = args.type
        
        # Model name based on type
        if self.weapon_type == "knife":
            self.model_name = "v_knife_t"
        elif self.weapon_type == "pistol":
            self.model_name = "v_pistol_usp"
        else:
            raise ValueError(f"[init] provided type {self.weapon_type}. Must be 'knife' or 'pistol'")
        
        self.crowbar = Path(__file__).parent / "thirdparty" / "CrowbarDecompiler(1.1).exe"
        self.studiomdl = self.game_dir / "bin" / "win64" / "studiomdl.exe"
        self.gameinfo = self.game_dir / "momentum" / "gameinfo.txt"
        self.weapon_model = self.data_dir / args.weapon
        self.weapon_anim = self.data_dir / args.weapon.replace('.mdl', '_anim.mdl')
        self.glove_model = self.data_dir / args.gloves

        required_paths = [
            (self.data_dir, "Data"),
            (self.game_dir, "Game"),
            (self.crowbar, "Crowbar"),
            (self.studiomdl, "Studiomdl"),
            (self.weapon_model, "Weapon model"),
            (self.glove_model, "Glove model"),
            (self.scripts_dir, "Scripts")
        ]
        
        for path, description in required_paths:
            if not path.exists():
                raise ValueError(f"{description} not found: {path}")
        

    def decompile_model(self, model_path, output_dir):
        """Decompile mdl"""
        if not model_path.exists():
            print(f"[decompile_model] Model not found: {model_path}")
            return None
        
        output_dir.mkdir(parents=True, exist_ok=True)
        cmd = [str(self.crowbar), str(model_path), str(output_dir)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        if file.endswith('.smd'):
                            smd_path = Path(root) / file
                            print(f"[decompile_model] Found SMD: {smd_path.name}")
                            return smd_path
        except Exception as e:
            print(f"[decompile_model] Failed: {e}")
        return None
    

    def copy_animations(self, anim_model, temp_dir, output_dir):
        """Copy animations"""
        if not anim_model.exists():
            return None, None
        
        anim_dir = temp_dir / "anim"
        anim_smd = self.decompile_model(anim_model, anim_dir)

        if not anim_smd:
            return None, None
        
        qc_files = list(anim_dir.glob("*.qc"))
        if not qc_files:
            return None, None
        
        anim_qc = qc_files[0]
        anim_name = anim_model.stem
        anim_smd_dir = anim_dir / f"{anim_name}_anims"
        
        if not anim_smd_dir.exists():
            return str(anim_qc), None
         
        # todo (paths)
        anim_output_dir = output_dir / f"{self.model_name}_anims"
        anim_output_dir.mkdir(parents=True, exist_ok=True)
        
        for anim_file in anim_smd_dir.glob("*.smd"):
            dst = anim_output_dir / anim_file.name
            shutil.copy2(anim_file, dst)
            print(f"[copy_animations] Copied: {anim_file.name}")
        
        return str(anim_qc), str(anim_output_dir)
    
    def generate_qc(self, weapon_qc_path, glove_qc_path, anim_qc_path, output_qc_path):
        """Generate QC (bodygroup approach)"""
        
        with open(weapon_qc_path, 'r', encoding='utf-8') as f:
            weapon_qc_content = f.read()
        
        with open(glove_qc_path, 'r', encoding='utf-8') as f:
            glove_qc_content = f.read()
        
        # todo (paths)
        qc_lines = []
        qc_lines.append(f'$modelname "weapons/{self.model_name}.mdl"')
        qc_lines.append('')
        
        qc_lines.append('$bodygroup "knife"')
        qc_lines.append('{')
        qc_lines.append(f'    studio "{Path(self.weapon_model).stem}.smd"')
        qc_lines.append('}')
        qc_lines.append('')
        
        qc_lines.append('$bodygroup "gloves"')
        qc_lines.append('{')
        qc_lines.append(f'    studio "{Path(self.glove_model).stem}.smd"')
        qc_lines.append('}')
        qc_lines.append('')
        
        qc_lines.append('$surfaceprop "weapon"')
        qc_lines.append('$contents "solid"')
        qc_lines.append('$illumposition 0 0 0')
        
        # TODO: material search paths
        qc_lines.append('$cdmaterials "models/weapons/"')
        qc_lines.append('$cdmaterials "models/weapons/v_models/knife_m9_bay/"')
        qc_lines.append('$cdmaterials "models/weapons/v_models/arms/glove_sporty/"')
        qc_lines.append('$cdmaterials "models/weapons/v_models/arms/"')
        qc_lines.append('$cdmaterials "models/arms/"')
        qc_lines.append('$cdmaterials "materials/models/weapons/v_models/arms/glove_sporty/"')
        qc_lines.append('$cdmaterials ""')
        qc_lines.append('')
        
        # Use only knife bone definitions (with bonemerge and bonesaveframe)
        weapon_lines = weapon_qc_content.split('\n')
        for line in weapon_lines:
            line = line.strip()
            if (line.startswith('$definebone') or
                line.startswith('$attachment') or
                line.startswith('$bbox') or
                line.startswith('$cbox') or
                line.startswith('$bonemerge') or
                line.startswith('$bonesaveframe')):
                qc_lines.append(line)
        
        qc_lines.append('')
        
        # Add animations using includemodel
        qc_lines.append('$includemodel "weapons/v_knife_m9_bay_anim.mdl"')
        
        with open(output_qc_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(qc_lines))
        
        print(f"[generate_qc] QC generated: {output_qc_path}")
    
    def compile_model(self, qc_path, work_dir):
        """Compile model"""
        try:
            temp_game_dir = work_dir / "temp_game"
            temp_game_dir.mkdir(exist_ok=True)
            
            gameinfo_dest = temp_game_dir / "gameinfo.txt"
            shutil.copy2(self.gameinfo, gameinfo_dest)
            
            cmd = [
                str(self.studiomdl),
                "-verbose",
                "-game", str(temp_game_dir),
                "-nop4",
                str(qc_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(work_dir))
            
            print(f"[compile_model] Return code: {result.returncode}")
            if result.stdout:
                print(f"[compile_model] Compilation output: {result.stdout[-1000:]}")
            
            if result.returncode == 0:
                qc_name = Path(qc_path).stem
                models_dir = temp_game_dir / "models" / "weapons"
                
                if models_dir.exists():
                    moved_count = 0
                    for file in models_dir.iterdir():
                        if file.stem.startswith(qc_name):
                            dst = work_dir / file.name
                            shutil.move(str(file), str(dst))
                            size = dst.stat().st_size
                            print(f"[compile_model] Created: {file.name} ({size:,} bytes)")
                            moved_count += 1
                    
                    shutil.rmtree(temp_game_dir, ignore_errors=True)
                    return moved_count >= 3
            else:
                if result.stderr:
                    print(f"[compile_model] Compilation error: {result.stderr}")
            
            return False
        except Exception as e:
            print(f"[compile_model] Compilation error: {e}")
            return False
    
    def copy_scripts(self):
        """Copy weapon scripts based on type"""
        try:
            scripts_output_dir = Path(self.output_dir).parent.parent / "scripts"
            scripts_output_dir.mkdir(parents=True, exist_ok=True)

            if self.weapon_type == "knife":
                source_script = self.scripts_dir / "weapon_momentum_knife.txt"
                target_script = scripts_output_dir / "weapon_momentum_knife.txt"
            elif self.weapon_type == "pistol":
                source_script = self.scripts_dir / "weapon_momentum_pistol.txt"
                target_script = scripts_output_dir / "weapon_momentum_pistol.txt"
            else:
                print(f"[copy_scripts] Unknown weapon type: {self.weapon_type}")
                return False
            
            shutil.copy2(source_script, target_script)
            
            print(f"[copy_scripts] Copied: {source_script.name} -> {target_script.name}")
            return True
            
        except Exception as e:
            print(f"[copy_scripts] Error: {e}")
            return False
    
    def main(self):
        """Run conversion"""
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Decompile both models (separately)
            print("[main] 1. Decompiling models")
            weapon_dir = temp_path / "knife"
            glove_dir = temp_path / "glove"
            
            weapon_smd = self.decompile_model(self.weapon_model, weapon_dir)
            glove_smd = self.decompile_model(self.glove_model, glove_dir)
            
            if not weapon_smd or not glove_smd:
                return False
            
            # Find QC files
            weapon_qc = list(weapon_dir.glob("*.qc"))[0]
            glove_qc = list(glove_dir.glob("*.qc"))[0]
            
            # Copy SMDs (no merging)
            print("\n[main] 2. Copying SMDs")
            weapon_output = self.output_dir / f"{Path(self.weapon_model).stem}.smd"
            glove_output = self.output_dir / f"{Path(self.glove_model).stem}.smd"
            
            shutil.copy2(weapon_smd, weapon_output)
            shutil.copy2(glove_smd, glove_output)
            
            print(f"[main] Copied: {weapon_smd.name} -> {weapon_output.name}")
            print(f"[main] Copied: {glove_smd.name} -> {glove_output.name}")
            
            # Animations
            print("\n[main] 3. Processing animations")
            anim_qc, anim_dir = self.copy_animations(self.weapon_anim, temp_path, self.output_dir)
            
            # Generate QC
            print("\n[main] 4. Generating QC")
            final_qc = self.output_dir / f"{self.model_name}.qc"
            self.generate_qc(weapon_qc, glove_qc, anim_qc, final_qc)
            
            # Compile
            print("\n[main] 5. Compiling")
            success = self.compile_model(final_qc, self.output_dir)
            
            # Copy scripts
            if success:
                print("\n[main] 6. Copying scripts")
                script_success = self.copy_scripts()
                if not script_success:
                    print("[main] Script copying failed")
            
            print(f"[main] Result: {'SUCCESS' if success else 'FAILED'}")
            return success

def parse_args():
    """Command line"""
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-data', required=True, help='CS:GO data')
    parser.add_argument('-game', required=True, help='Momentum directory')
    parser.add_argument('-output', required=True, help='Output directory')
    parser.add_argument('-weapon', required=True, help='Weapon model path')
    parser.add_argument('-gloves', required=True, help='Glove model path')
    parser.add_argument('-type', required=True, choices=['knife', 'pistol'], help='Knife or Pistol')

    return parser.parse_args()

if __name__ == "__main__":
    try:
        args = parse_args()
        converter = Converter(args)
        success = converter.main()
        
        if success:
            print(f"\n[skin2momentum] Model '{converter.model_name}.mdl' created")
        else:
            print(f"\n[skin2momentum] FAIL")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[skin2momentum] ERROR: {e}")
        sys.exit(1)