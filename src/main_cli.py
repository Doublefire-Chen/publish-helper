#!/usr/bin/env python3
"""
Publish Helper - Interactive CLI Mode
Provides a command-line interface for the one-key workflow.

Usage:
    python src/main_cli.py
"""
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.mediainfo import get_media_info
from src.core.picturebed import upload_picture
from src.core.ptgen import get_pt_gen_description
from src.core.rename import get_pt_gen_info, get_video_info, get_name_from_template, rename_file, rename_folder
from src.core.screenshot import get_screenshot, get_thumbnail
from src.core.tool import get_settings, check_path_and_find_video, make_torrent, chinese_name_to_pinyin


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header():
    """Print the CLI header."""
    print(f"\n{Colors.CYAN}{'='*50}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  Publish Helper - Interactive CLI{Colors.END}")
    print(f"{Colors.CYAN}{'='*50}{Colors.END}\n")


def print_step(step_num, total, message):
    """Print a step indicator."""
    print(f"{Colors.BLUE}[{step_num}/{total}]{Colors.END} {message}")


def print_success(message):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_warning(message):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def prompt(message, default=None):
    """Prompt user for input."""
    if default:
        user_input = input(f"{Colors.BOLD}{message}{Colors.END} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{Colors.BOLD}{message}{Colors.END}: ").strip()


def select_content_type():
    """Prompt user to select content type."""
    print(f"{Colors.BOLD}请选择内容类型 / Select content type:{Colors.END}")
    print("  [1] 电影 Movie")
    print("  [2] 剧集 TV Series")
    print("  [3] 短剧 Playlet")
    print()
    
    while True:
        choice = prompt("选择 / Choice", "1")
        if choice in ['1', '2', '3']:
            return {'1': 'movie', '2': 'tv', '3': 'playlet'}[choice]
        print_error("请输入 1, 2, 或 3")


def process_movie(resource_url, video_path):
    """Process a movie with the one-key workflow."""
    total_steps = 6
    
    # Step 1: Get PT-Gen description
    print_step(1, total_steps, "获取 PT-Gen 信息...")
    pt_gen_api_url = get_settings('pt_gen_api_url')
    
    success, response = get_pt_gen_description(pt_gen_api_url, resource_url)
    if not success:
        print_error(f"获取 PT-Gen 失败: {response}")
        return False
    
    description = response
    print_success("PT-Gen 信息获取成功")
    
    # Step 2: Parse PT-Gen info
    print_step(2, total_steps, "解析 PT-Gen 信息...")
    try:
        original_title, english_title, year, other_names, categories, actors, episodes, season = get_pt_gen_info(description)
    except Exception as e:
        print_error(f"解析 PT-Gen 失败: {e}")
        return False
    
    if not year:
        print_error("未能获取年份信息")
        return False
    
    print_success(f"标题: {original_title or english_title} ({year})")
    
    # Handle missing English title
    if not english_title and original_title:
        print_warning("未找到英文名称，尝试生成拼音...")
        english_title = chinese_name_to_pinyin(original_title)
        if english_title:
            print_success(f"拼音名称: {english_title}")
    
    # Step 3: Get video info
    print_step(3, total_steps, "获取视频信息...")
    is_video_path, video_file = check_path_and_find_video(video_path)
    if is_video_path not in [1, 2]:
        print_error(f"视频路径无效: {video_file}")
        return False
    
    success, video_info = get_video_info(video_file)
    if not success:
        print_error(f"获取视频信息失败: {video_info}")
        return False
    
    video_format, video_codec, bit_depth, hdr_format, frame_rate, audio_codec, channels, audio_num = video_info[:8]
    print_success(f"视频格式: {video_format} {video_codec}")
    
    # Step 4: Get MediaInfo
    print_step(4, total_steps, "获取 MediaInfo...")
    success, media_info = get_media_info(video_file)
    if success:
        print_success("MediaInfo 获取成功")
    else:
        print_warning(f"MediaInfo 获取失败: {media_info}")
        media_info = ""
    
    # Step 5: Generate file name
    print_step(5, total_steps, "生成文件名...")
    source = get_settings('default_source') or 'WEB-DL'
    team = get_settings('default_team') or 'Anonymous'
    
    other_titles_str = ' / '.join(other_names) if other_names else ''
    actors_str = ' / '.join(actors) if actors else ''
    
    file_name = get_name_from_template(
        english_title, original_title, '', '', year,
        video_format, source, video_codec, bit_depth, hdr_format,
        frame_rate, audio_codec, channels, audio_num, team,
        other_titles_str, '', '', '', categories, actors_str,
        'file_name_movie'
    )
    
    main_title = get_name_from_template(
        english_title, original_title, '', '', year,
        video_format, source, video_codec, bit_depth, hdr_format,
        frame_rate, audio_codec, channels, audio_num, team,
        other_titles_str, '', '', '', categories, actors_str,
        'main_title_movie'
    )
    
    print_success(f"主标题: {main_title}")
    print_success(f"文件名: {file_name}")
    
    # Step 6: Summary
    print_step(6, total_steps, "生成摘要...")
    
    print(f"\n{Colors.CYAN}{'='*50}{Colors.END}")
    print(f"{Colors.BOLD}处理结果 / Results:{Colors.END}")
    print(f"  标题: {original_title}")
    print(f"  英文: {english_title}")
    print(f"  年份: {year}")
    print(f"  类别: {categories}")
    print(f"  格式: {video_format} {video_codec} {hdr_format}")
    print(f"  文件名: {file_name}")
    print(f"{Colors.CYAN}{'='*50}{Colors.END}")
    
    # Ask if user wants to continue with rename/screenshot/torrent
    print(f"\n{Colors.BOLD}是否继续执行以下操作? / Continue with?{Colors.END}")
    print("  - 重命名文件/文件夹")
    print("  - 生成截图")
    print("  - 上传图床")
    print("  - 制作种子")
    
    choice = prompt("\n继续? [y/N]", "n")
    if choice.lower() != 'y':
        print_warning("操作已取消")
        return True
    
    # Execute additional operations
    print(f"\n{Colors.BOLD}执行后续操作...{Colors.END}")
    
    # Rename
    do_rename = get_settings('rename_file')
    if do_rename:
        print("正在重命名...")
        if is_video_path == 1:  # Single file
            success, new_path = rename_file(video_file, file_name)
        else:  # Directory
            success, new_path = rename_folder(video_path, file_name)
        
        if success:
            print_success(f"重命名成功: {new_path}")
            video_path = new_path if is_video_path == 2 else os.path.dirname(new_path)
        else:
            print_error(f"重命名失败: {new_path}")
    
    # Screenshots
    screenshot_storage = get_settings('screenshot_storage_path')
    screenshot_num = int(get_settings('screenshot_number') or 4)
    
    print("正在生成截图...")
    success, screenshots = get_screenshot(video_file, screenshot_storage, screenshot_num, 0.02, 0.1, 0.9)
    if success:
        print_success(f"截图生成成功: {len(screenshots)} 张")
    else:
        print_error(f"截图失败: {screenshots}")
    
    # Torrent
    print("正在制作种子...")
    success, torrent_result = make_torrent(video_path)
    if success:
        print_success(f"种子制作成功: {torrent_result}")
    else:
        print_error(f"种子制作失败: {torrent_result}")
    
    print(f"\n{Colors.GREEN}{'='*50}")
    print(f"  ✓ 处理完成! / Processing Complete!")
    print(f"{'='*50}{Colors.END}\n")
    
    return True


def main():
    """Main entry point for interactive CLI."""
    print_header()
    
    # Select content type
    content_type = select_content_type()
    print()
    
    # Get resource URL
    resource_url = prompt("请输入资源链接 (豆瓣/IMDB URL)")
    if not resource_url:
        print_error("资源链接不能为空")
        return 1
    print()
    
    # Get video path
    video_path = prompt("请输入视频文件或文件夹路径")
    if not video_path:
        print_error("视频路径不能为空")
        return 1
    
    # Expand user path and check existence
    video_path = os.path.expanduser(video_path)
    if not os.path.exists(video_path):
        print_error(f"路径不存在: {video_path}")
        return 1
    print()
    
    # Process based on content type
    print(f"{Colors.BOLD}开始处理 / Starting...{Colors.END}\n")
    
    if content_type == 'movie':
        success = process_movie(resource_url, video_path)
    elif content_type == 'tv':
        print_warning("剧集处理暂未实现，请使用 GUI 模式")
        success = False
    else:
        print_warning("短剧处理暂未实现，请使用 GUI 模式")
        success = False
    
    return 0 if success else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}操作已取消{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print_error(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
