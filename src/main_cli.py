#!/usr/bin/env python3
"""
Publish Helper - Interactive CLI Mode
Provides a command-line interface for the one-key workflow.

Usage:
    python src/main_cli.py
"""
# isort: skip_file
# NOTE: Import order is critical - stdlib must come before local imports
# to avoid UnboundLocalError with os module
from src.core.autofeed import get_auto_feed_link
from src.core.mediainfo import get_media_info
from src.core.picturebed import upload_picture
from src.core.ptgen import get_pt_gen_description
from src.core.rename import (
    create_hard_link,
    get_name_from_template,
    get_pt_gen_info,
    get_video_info,
    move_file_to_folder,
    rename_file,
    rename_folder,
)
from src.core.screenshot import get_screenshot, get_thumbnail
from src.core.tool import (
    check_path_and_find_video,
    chinese_name_to_pinyin,
    get_settings,
    make_torrent,
)
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def print_settings_summary():
    """Print active settings summary."""
    print(f"{Colors.BOLD}当前配置 / Current Settings:{Colors.END}")

    # File management
    rename_file = get_settings('rename_file') == 'True'
    make_dir = get_settings('make_dir') == 'True'
    create_hardlink = get_settings('create_hard_link') == 'True'

    # Screenshot settings
    auto_upload = get_settings('auto_upload_screenshot') == 'True'
    delete_after_upload = get_settings('delete_screenshot') == 'True'
    do_thumbnail = get_settings('do_get_thumbnail') == 'True'
    screenshot_num = get_settings('screenshot_number')

    print(
        f"  文件管理: 重命名={_status(rename_file)} | 创建目录={_status(make_dir)} | 硬链接={_status(create_hardlink)}")
    print(f"  截图设置: 数量={screenshot_num} | 缩略图={_status(do_thumbnail)} | 自动上传={_status(auto_upload)} | 上传后删除={_status(delete_after_upload)}")
    print()


def _status(enabled):
    """Format boolean status for display."""
    return f"{Colors.GREEN}✓{Colors.END}" if enabled else f"{Colors.RED}✗{Colors.END}"


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
        user_input = input(
            f"{Colors.BOLD}{message}{Colors.END} [{default}]: ").strip()
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


def select_from_combo_box(label, combo_data_name):
    """
    Interactive selection from combo box data with numbered options.
    User can select by number or enter custom value.

    Args:
        label: Display label (e.g., "来源 Source")
        combo_data_name: Name of combo box data ('source', 'team', etc.)

    Returns:
        Selected or custom value
    """
    from src.core.tool import get_combo_box_data

    print(f"\n{Colors.BOLD}选择 {label}:{Colors.END}")

    # Get combo box data
    success, data_list = get_combo_box_data(combo_data_name)

    if not success or not data_list:
        # Fallback if no data available
        return prompt(f"{label}", "")

    # Filter out empty strings and display options
    valid_options = [item for item in data_list if item.strip()]

    if not valid_options:
        return prompt(f"{label}", "")

    # Display numbered options
    for idx, option in enumerate(valid_options, 1):
        print(f"  [{idx}] {option}")
    print(f"  [0] 自定义 / Custom")
    print()

    while True:
        choice = prompt(f"选择数字或直接输入 / Select number or enter custom", "1")

        # Check if it's a number selection
        if choice.isdigit():
            choice_num = int(choice)
            if choice_num == 0:
                # Custom input
                custom = prompt(f"输入自定义 {label}", "")
                return custom if custom else valid_options[0]
            elif 1 <= choice_num <= len(valid_options):
                return valid_options[choice_num - 1]
            else:
                print_error(f"请输入 0-{len(valid_options)} 之间的数字")
        else:
            # Direct custom input
            return choice if choice else valid_options[0]


def process_movie(resource_url, video_path):
    """Process a movie with the one-key workflow."""
    total_steps = 6

    # Step 1: Get PT-Gen description
    print_step(1, total_steps, "获取 PT-Gen 信息...")
    pt_gen_api_url = get_settings('pt_gen_api_url')

    success, response = get_pt_gen_description(pt_gen_api_url, resource_url)
    if not success:
        print_warning(f"主接口失败: {response}")

        # Try backup API
        pt_gen_api_url_backup = get_settings('pt_gen_api_url_backup')
        if pt_gen_api_url_backup and pt_gen_api_url_backup != pt_gen_api_url:
            print(f"  尝试备用接口: {pt_gen_api_url_backup}")
            success, response = get_pt_gen_description(
                pt_gen_api_url_backup, resource_url)
            if not success:
                print_error(f"备用接口也失败: {response}")
                return False
            print_success("备用接口获取成功")
        else:
            print_error("未配置备用接口或备用接口与主接口相同")
            return False

    # Response is a tuple (description_text, response_dict)
    # Extract just the description text for parsing
    if isinstance(response, tuple):
        description = response[0]  # First element is the formatted description
    else:
        description = response

    print_success("PT-Gen 信息获取成功")

    # Step 2: Parse PT-Gen info
    print_step(2, total_steps, "解析 PT-Gen 信息...")
    try:
        original_title, english_title, year, other_names, categories, actors, episodes, season = get_pt_gen_info(
            description)
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

    video_format, video_codec, bit_depth, hdr_format, frame_rate, audio_codec, channels, audio_num = video_info[
        :8]
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

    # Interactive selection for source and team
    source = select_from_combo_box("来源 Source", "source")
    team = select_from_combo_box("制作组 Team", "team")

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

    # Rename (matching GUI logic exactly)
    do_rename = get_settings('rename_file') == 'True'
    make_dir = get_settings('make_dir') == 'True'
    create_hardlink = get_settings('create_hard_link') == 'True'

    if do_rename:
        print("正在重命名...")
        if is_video_path == 1:  # Single file
            # If make_dir is enabled, move file into a folder first
            if make_dir:
                print("  创建目录并移动文件...")
                move_success, new_file_path = move_file_to_folder(
                    video_file, file_name)
                if move_success:
                    print_success(f"  文件已移动到目录: {new_file_path}")
                    video_file = new_file_path
                    video_path = os.path.dirname(new_file_path)
                    # Now rename the directory (same as GUI logic)
                    print("  对文件夹重新命名...")
                    rename_directory_success, response = rename_folder(
                        video_path, file_name)
                    if rename_directory_success:
                        video_path = response
                        print_success(f"  视频文件夹成功重新命名为：{video_path}")
                        # Re-check and find video file in renamed directory
                        is_video_path, response = check_path_and_find_video(
                            video_path)
                        if is_video_path == 2:
                            video_file = response
                            print_success(f"  成功读取到视频文件：{video_file}")
                        else:
                            print_error(f"  读取视频文件失败：{response}")
                            return False
                    else:
                        print_error(f"  重命名失败：{response}")
                        return False
                else:
                    print_error(f"  移动文件失败: {new_file_path}")
                    return False

                # After folder rename, also rename the file inside (GUI does both)
                print("  开始对文件重新命名...")
                rename_file_success, response = rename_file(
                    video_file, file_name)
                if rename_file_success:
                    video_file = response
                    print_success(f"  视频文件成功重新命名为：{video_file}")
                else:
                    print_error(f"  重命名失败：{response}")
                    return False
            else:
                # Just rename the file without making directory
                success, new_path = rename_file(video_file, file_name)
                if success:
                    new_path = os.path.normpath(new_path)
                    print_success(f"重命名成功: {new_path}")
                    video_file = new_path
                    video_path = os.path.dirname(new_path)
                else:
                    print_error(f"重命名失败: {new_path}")
                    return False

        else:  # Directory (is_video_path == 2)
            # First rename the folder
            print("  对文件夹重新命名...")
            rename_directory_success, response = rename_folder(
                video_path, file_name)
            if rename_directory_success:
                video_path = response
                print_success(f"  视频文件夹成功重新命名为：{video_path}")
                # Re-check and find video file in renamed directory
                is_video_path, response = check_path_and_find_video(video_path)
                if is_video_path == 2:
                    video_file = response
                    print_success(f"  成功读取到视频文件：{video_file}")
                else:
                    print_error(f"  读取视频文件失败：{response}")
                    return False
            else:
                print_error(f"  重命名失败：{response}")
                return False

            # Then rename the file inside the folder (GUI does both)
            print("  开始对文件重新命名...")
            rename_file_success, response = rename_file(video_file, file_name)
            if rename_file_success:
                video_file = response
                print_success(f"  视频文件成功重新命名为：{video_file}")
            else:
                print_error(f"  重命名失败：{response}")
                return False

        print_success("重命名全部成功")

    # Create hard link if enabled
    if create_hardlink:
        print("正在创建硬链接...")
        hardlink_success, hardlink_path = create_hard_link(video_path)
        if hardlink_success:
            print_success(f"硬链接创建成功: {hardlink_path}")
        else:
            print_error(f"硬链接创建失败: {hardlink_path}")

    # Screenshots
    screenshot_storage = get_settings('screenshot_storage_path')
    screenshot_num = int(get_settings('screenshot_number') or 4)
    screenshot_threshold = float(get_settings('screenshot_threshold') or 30.0)
    screenshot_start_percentage = float(
        get_settings('screenshot_start_percentage') or 0.10)
    screenshot_end_percentage = float(
        get_settings('screenshot_end_percentage') or 0.90)
    do_get_thumbnail = get_settings('do_get_thumbnail') == 'True'
    thumbnail_rows = int(get_settings('thumbnail_rows') or 3)
    thumbnail_cols = int(get_settings('thumbnail_cols') or 3)
    auto_upload_screenshot = get_settings('auto_upload_screenshot') == 'True'
    delete_screenshot = get_settings('delete_screenshot') == 'True'

    print("正在生成截图...")
    pictures = []
    success, screenshots = get_screenshot(video_file, screenshot_storage, screenshot_num,
                                          screenshot_threshold, screenshot_start_percentage,
                                          screenshot_end_percentage, screenshot_min_interval=0.01)
    if success:
        print_success(f"截图生成成功: {len(screenshots)} 张")
        pictures = screenshots

        # Generate thumbnail if enabled
        if do_get_thumbnail:
            from src.core.screenshot import get_thumbnail
            print("正在生成缩略图...")
            thumbnail_success, thumbnail_path = get_thumbnail(
                video_file, screenshot_storage, thumbnail_rows, thumbnail_cols,
                screenshot_start_percentage, screenshot_end_percentage
            )
            if thumbnail_success:
                print_success(f"缩略图生成成功: {thumbnail_path}")
                # Add thumbnail at the beginning
                pictures.insert(0, thumbnail_path)
            else:
                print_warning(f"缩略图生成失败: {thumbnail_path}")

        # Upload to picture bed if enabled
        if auto_upload_screenshot and pictures:
            picture_bed_api_url = get_settings('picture_bed_api_url')
            picture_bed_api_token = get_settings('picture_bed_api_token')

            print(f"正在上传 {len(pictures)} 张图片到图床...")
            uploaded_urls = []

            for idx, picture_path in enumerate(pictures, 1):
                print(f"  上传第 {idx}/{len(pictures)} 张...")
                upload_success, response = upload_picture(
                    picture_bed_api_url, picture_bed_api_token, picture_path)

                if upload_success:
                    uploaded_urls.append(response)
                    print_success(f"    上传成功")

                    # Delete local screenshot if setting enabled
                    if delete_screenshot:
                        try:
                            os.remove(picture_path)
                            print(f"    本地文件已删除: {picture_path}")
                        except Exception as e:
                            print_warning(f"    删除本地文件失败: {e}")
                else:
                    print_error(f"    上传失败: {response}")
                    # Keep local path if upload fails
                    uploaded_urls.append(picture_path)

            if uploaded_urls:
                print_success(f"图片链接 ({len(uploaded_urls)} 张):")
                for url in uploaded_urls:
                    print(f"  {url}")
        else:
            if not auto_upload_screenshot:
                print_success(f"本地截图路径:")
                for pic in pictures:
                    print(f"  {pic}")
    else:
        print_error(f"截图失败: {screenshots}")

    # Torrent
    torrent_storage = get_settings('torrent_storage_path')
    print("正在制作种子...")
    success, torrent_result = make_torrent(video_path, torrent_storage)
    torrent_path = ""
    if success:
        print_success(f"种子制作成功: {torrent_result}")
        torrent_path = torrent_result
    else:
        print_error(f"种子制作失败: {torrent_result}")

    # Generate auto-feed link
    print("\n正在生成 Auto-Feed 链接...")
    category = '电影'
    torrent_url = ""  # Can be filled if torrent is uploaded somewhere

    get_auto_feed_link_success, response = get_auto_feed_link(
        main_title, f"{original_title} / {other_titles_str} | 类型：{categories} | 演员：{actors_str}",
        description, media_info, file_name, team, source, category, torrent_url
    )

    if get_auto_feed_link_success:
        auto_feed_link = response
        print_success("Auto-Feed 链接已生成")
        print(f"\n{Colors.BOLD}Auto-Feed 链接:{Colors.END}")
        print(f"{Colors.CYAN}{auto_feed_link}{Colors.END}")
        print(
            f"\n{Colors.YELLOW}请复制上方链接到浏览器中打开 / Copy the link above to browser{Colors.END}\n")
    else:
        print_warning(f"Auto-Feed 链接生成失败: {response}")

    print(f"\n{Colors.GREEN}{'='*50}")
    print(f"  ✓ 处理完成! / Processing Complete!")
    print(f"{'='*50}{Colors.END}\n")

    return True


def main():
    """Main entry point for interactive CLI."""
    print_header()
    print_settings_summary()

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

    # Strip surrounding quotes (common when pasting paths on Windows)
    video_path = video_path.strip('"\'')

    # Expand user path and normalize for cross-platform
    video_path = os.path.expanduser(video_path)
    video_path = os.path.normpath(video_path)

    # On Windows, expand short (8.3) paths to long paths progressively
    if sys.platform == 'win32' and '~' in video_path:
        try:
            import ctypes
            from ctypes import wintypes

            # GetLongPathNameW to convert short paths
            _GetLongPathNameW = ctypes.windll.kernel32.GetLongPathNameW
            _GetLongPathNameW.argtypes = [
                wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
            _GetLongPathNameW.restype = wintypes.DWORD

            # Try to expand progressively from root to handle partially invalid paths
            parts = video_path.split(os.sep)
            expanded_path = parts[0]  # Start with drive letter (e.g., 'C:')

            for part in parts[1:]:
                test_path = os.path.join(expanded_path, part)
                if os.path.exists(test_path):
                    # Try to expand this existing part
                    buffer_size = 512
                    buffer = ctypes.create_unicode_buffer(buffer_size)
                    ret = _GetLongPathNameW(test_path, buffer, buffer_size)
                    if ret != 0:
                        expanded_path = buffer.value
                    else:
                        expanded_path = test_path
                else:
                    # Path doesn't exist, keep short name
                    expanded_path = test_path

            if expanded_path != video_path:
                print(f"  展开路径为: {expanded_path}")
                video_path = expanded_path
        except Exception as e:
            print_warning(f"  无法展开短路径: {e}")

    if not os.path.exists(video_path):
        print_error(f"路径不存在: {video_path}")
        print_warning("提示: 请在文件资源管理器中右键复制文件路径，或拖拽文件到终端")

        # Try to show which part of the path doesn't exist
        if sys.platform == 'win32':
            parts = video_path.split(os.sep)
            test_path = parts[0]
            for i, part in enumerate(parts[1:], 1):
                test_path = os.path.join(test_path, part)
                if not os.path.exists(test_path):
                    print_warning(f"  不存在的部分从这里开始: {test_path}")
                    break
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
