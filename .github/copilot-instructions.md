# ComfyU-auto-script: Copilot Instructions

## Project Overview
ComfyU-auto-script is a Python-based data cleaning and YAML management tool for ComfyUI (a generative AI framework). It processes character and LoRA model metadata stored in YAML files, applying tag filtering, normalization, and automated key population based on configuration rules and SafeTensors model metadata.

## Architecture & Data Flow

### Three-Layer Design
1. **Utils Layer** (`utils/`) - Reusable modules for core operations
   - `config_loader.py`: Loads unified `config.yml` (keys: `comfui_dir`, `data_dir`, `types`)
   - `yaml_handler.py`: Uses `ruamel.yaml` to preserve comments/formatting during YAML edits
   - `tag_processor.py`: Tag normalization (underscore→space), regex-based exclusion patterns, tag filtering
   - `safetensors_reader.py`: Extracts `ss_tag_frequency` metadata from model files

2. **Scripts Layer** (`scripts/`) - Executable workflows for char/lora YAML operations
   - Scripts follow naming: `{action}_{type}_{model}.py` (e.g., `remove_excluded_tags_char.py`)
   - Import utils via `sys.path.insert(0, script_dir)` before importing utils module
   - Each script operates independently on specific YAML files in `data_dir`

3. **Configuration Layer** (`config.yml`)
   - Section-based structure: `char:` and `lora:` subsections
   - Supports regex patterns in excluded_tags using `/pattern/` syntax (e.g., `/cum .*/`)
   - Default paths: `W:\ComfyUI_windows_portable` and `W:\ComfyU-auto-script_data`

### Tag Processing Pipeline
1. Load source YAML (char.yml, lora.yml) from data_dir
2. Extract model metadata if applicable (SafeTensors ss_tag_frequency)
3. Apply TagProcessor operations:
   - Normalize tags (underscore→space, lowercase)
   - Filter against excluded_patterns (literal & regex)
   - Populate dress field with dress_tags
4. Preserve YAML formatting via YAMLHandler.save()

## Critical Patterns & Conventions

### YAML Field Structure (char.yml template)
```yaml
character_name:
  weight: 150
  positive:
    char: "1girl , "        # Character tags (filtered by excluded_tags)
    dress: "{  {tag1|tag2}  |4::__dress__},"  # Dress options with weighted format
```

### Tag Exclusion & Filtering
- **Literal tags**: Direct string match (e.g., `'looking at viewer'`)
- **Regex patterns**: Wrap in `/` delimiters in config, e.g., `'/cum .*/''` → matches any tag starting with "cum "
- Use `TagProcessor.is_tag_excluded()` for both pattern types
- Normalize tags before comparison to handle underscore variants

### SafeTensors Metadata Reading
- Access via `SafeTensorsReader.extract_ss_tag_frequency(file_path)`
- Returns dict mapping tags to frequency counts
- Used by fill_missing_tags_lora.py to populate lora.yml from model metadata

### Path Resolution
- Scripts calculate root via: `script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`
- All relative paths resolved from project root (parent of scripts/ and utils/)
- ConfigLoader defaults to `{root}/config.yml` if no path specified

## Development Workflows

### Adding a New Script
1. Create `scripts/{action}_{context}_{model}.py`
2. Import utils: `sys.path.insert(0, script_dir); from utils import ConfigLoader, TagProcessor, YAMLHandler`
3. Load config: `config = ConfigLoader()`
4. Follow template: load YAML → apply logic → save with YAMLHandler.save()
5. Add corresponding .cmd wrapper for Windows users

### Testing Tag Filtering Logic
- Use `TagProcessor.normalize_tag()` to verify underscore/space handling
- Test regex patterns with `/pattern/` wrapper via `TagProcessor.is_tag_excluded()`
- Validate excluded_tags config format (no regex delimiters for literal patterns)

### Common Issues
- **Import errors**: Ensure `sys.path.insert(0, script_dir)` before utils import
- **YAML corruption**: Always use `YAMLHandler` for write operations to preserve formatting
- **Tag mismatches**: Normalize tags before comparison (underscore→space)
- **SafeTensors decode errors**: Check file path exists and is valid safetensors format

## Key Files Reference
- Configuration: [config.yml](../config.yml) - Single source of truth for all paths & tag rules
- Core utilities: [utils/](../utils) - All reusable logic lives here
- Scripts: [scripts/](../scripts) - Entry points for batch operations
- Metadata reading: [utils/safetensors_reader.py](../utils/safetensors_reader.py) - Model metadata extraction

## External Dependencies
- `ruamel.yaml`: YAML parsing with comment preservation (see requirements.txt)
- `safetensors`: Model metadata reading (optional, for fill_missing_tags_lora.py)
