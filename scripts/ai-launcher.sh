#!/bin/zsh
# 🚀 AI CLI Launcher with Enhanced Features
# Quick, reliable access to all AI coding assistants

# Note: we intentionally avoid `set -e` here because the launcher
# should remain interactive even when a target CLI is missing.

# Set up signal handling for graceful exit
trap 'echo -e "\n${CYAN}👋 Goodbye!${NC}"; exit 0' INT
trap 'echo -e "\n${CYAN}👋 Goodbye!${NC}"; exit 0' TERM

# Configuration files
LAST_SELECTION_FILE="$HOME/.ai-launcher-last"
CONFIG_FILE="$HOME/.ai-launcher-config"

# 🎨 Color palette for consistent UI
GREEN='\033[0;32m'    # Success messages
YELLOW='\033[1;33m'   # Warnings, highlights
RED='\033[0;31m'      # Errors
BLUE='\033[0;34m'     # Headers
CYAN='\033[0;36m'     # Prompts, info
BOLD='\033[1m'        # Emphasis
NC='\033[0m'          # No Color (reset)

# Function to check if a command exists
check_command_exists() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}❌ Error: $1 is not installed or not in PATH${NC}"
        echo -e "${YELLOW}💡 Tip: Install $1 or check your PATH configuration${NC}"
        return 1
    fi
    return 0
}

# Function to display help
show_help() {
    clear
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                           📚 HELP                             ║${NC}"
    echo -e "${BLUE}╠══════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${BLUE}║              🤖 AI CLI Launcher - User Guide                   ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}🎯 Navigation:${NC}"
    echo -e "  • ${BOLD}Numbers${NC}: Type 0-11 to select an option"
    echo -e "  • ${BOLD}Quick Keys${NC}: c=Claude, g=GitHub, o=OpenCode, etc."
    echo -e "  • ${BOLD}0${NC}: Repeat last selection (${YELLOW}🔄${NC})"
    echo -e "  • ${BOLD}h${NC}: Show this help (${YELLOW}📚${NC})"
    echo -e "  • ${BOLD}q${NC}: Quit anytime (${YELLOW}🚪${NC})"
    echo ""
    echo -e "${CYAN}⚙️  Additional Commands:${NC}"
    echo -e "  • ${BOLD}c${NC}: Clear last selection (${YELLOW}🧹${NC})"
    echo -e "  • ${BOLD}s${NC}: Show status (${YELLOW}📊${NC})"
    echo ""
    echo -e "${GREEN}💡 Pro Tips:${NC}"
    echo -e "  • Safe options: 1, 2, 5 (${YELLOW}[SAFE]${NC})"
    echo -e "  • Balanced options: 3, 4, 6, 7, 9 (${YELLOW}[BALANCED]${NC})"
    echo -e "  • Caution required: 8, 10 (${YELLOW}[⚠️ DANGEROUS]${NC})"
    echo ""
    echo -e "${CYAN}Press Enter to return to main menu...${NC}"
    read -r
}

# Function to display status
show_status() {
    clear
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                           📊 STATUS                           ║${NC}"
    echo -e "${BLUE}╠══════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${BLUE}║              🤖 AI CLI Tools Availability                      ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}🔍 Checking available tools...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    tools=("claude" "opencode" "codex" "copilot" "droid" "qwen" "gemini")
    for tool in "${tools[@]}"; do
        if check_command_exists "$tool"; then
            echo -e "  ${GREEN}✓${NC} $tool ${GREEN}(Available)${NC}"
        else
            echo -e "  ${RED}✗${NC} $tool ${RED}(Not found)${NC}"
        fi
    done

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}📁 Configuration:${NC}"
    echo -e "  ${CYAN}Last selection file:${NC} $LAST_SELECTION_FILE"
    if [ -f "$LAST_SELECTION_FILE" ]; then
        last_choice=$(cat "$LAST_SELECTION_FILE")
        # Get the name of last selection for display
        case $last_choice in
            1) last_name="Claude NEW" ;;
            2) last_name="Claude RESUME" ;;
            3) last_name="OpenCode" ;;
            4) last_name="Codex Full-Auto" ;;
            5) last_name="GitHub Copilot" ;;
            6) last_name="Droid Medium" ;;
            7) last_name="Qwen Auto-Edit" ;;
            8) last_name="Qwen YOLO" ;;
            9) last_name="Gemini Auto-Edit" ;;
            10) last_name="Gemini YOLO" ;;
            *) last_name="Unknown" ;;
        esac
        echo -e "  ${CYAN}Last selection:${NC} ${BOLD}$last_name${NC} (Option ${YELLOW}$last_choice${NC})"
    else
        echo -e "  ${YELLOW}No previous selection${NC}"
    fi
    echo ""
    echo -e "${CYAN}Press Enter to return to main menu...${NC}"
    read -r
}

# Function to clear last selection
clear_last_selection() {
    if [ -f "$LAST_SELECTION_FILE" ]; then
        rm "$LAST_SELECTION_FILE"
        echo -e "${GREEN}✅ Last selection cleared.${NC}"
        sleep 1
    else
        echo -e "${YELLOW}⚠️ No previous selection to clear.${NC}"
        sleep 1
    fi
}

# Function to validate and launch commands safely
launch_command() {
    local cmd_name="$1"
    shift  # Remove cmd_name from arguments
    local cmd_args=("$@")  # Store remaining arguments as an array

    if check_command_exists "$cmd_name"; then
        echo -e "${GREEN}🚀 INITIATING LAUNCH SEQUENCE${NC}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}🤖 Agent:${NC} ${BOLD}$cmd_name${NC}"
        echo -e "${CYAN}⚙️  Args:${NC} ${cmd_args[*]}"
        echo -e "${CYAN}⏱️  Starting in:${NC} ${YELLOW}3${NC} ... ${YELLOW}2${NC} ... ${YELLOW}1${NC} ... "
        sleep 2
        echo -e "${CYAN}⚡ EXECUTING ...${NC}"
        echo ""
        exec "$cmd_name" "${cmd_args[@]}"
    else
        echo -e "${RED}❌ COMMAND NOT FOUND${NC}"
        echo -e "${RED}   $cmd_name is not installed or not in PATH${NC}"
        echo -e "${YELLOW}💡 PRO TIP: Install $cmd_name or check your PATH configuration${NC}"
        echo -e "${CYAN}Press Enter to return to menu...${NC}"
        read -r
        # Never bubble a failure up to the main loop; keep UI alive
        return 0
    fi
}

# Read last selection if exists
LAST_CHOICE=""
LAST_NAME=""
if [ -f "$LAST_SELECTION_FILE" ]; then
    LAST_CHOICE=$(cat "$LAST_SELECTION_FILE")
    # Get the name of last selection for display
    case $LAST_CHOICE in
        1) LAST_NAME="Claude NEW" ;;
        2) LAST_NAME="Claude RESUME" ;;
        3) LAST_NAME="OpenCode" ;;
        4) LAST_NAME="Codex Full-Auto" ;;
        5) LAST_NAME="GitHub Copilot" ;;
        6) LAST_NAME="Droid Medium" ;;
        7) LAST_NAME="Qwen Auto-Edit" ;;
        8) LAST_NAME="Qwen YOLO" ;;
        9) LAST_NAME="Gemini Auto-Edit" ;;
        10) LAST_NAME="Gemini YOLO" ;;
    esac
fi

# Main menu loop
while true; do
    # Clear screen and show header
    clear
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    🤖 AI CLI LAUNCHER                         ║${NC}"
    echo -e "${BLUE}╠══════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${BLUE}║                Select Your AI Assistant                       ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Show last selection if available
    if [ -n "$LAST_NAME" ]; then
        echo -e "${CYAN}💾 Last used:${NC} ${BOLD}$LAST_NAME${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
    fi

    # Show the 0 option if there's a previous selection
    if [ -n "$LAST_CHOICE" ]; then
        echo -e "${CYAN}┌─ 🔄 Repeat last: $LAST_NAME${NC}"
        echo -e "${CYAN}│  ${YELLOW}0)${NC} Quick access to previous selection"
        echo -e "${BLUE}├─────────────────────────────────────────────────────────────────${NC}"
    else
        echo -e "${BLUE}┌─────────────────────────────────────────────────────────────────${NC}"
    fi

    # Display menu options with horizontal lines between tool providers
    echo -e "${CYAN}│${NC} ${YELLOW}1)${NC} Claude Code (NEW) - Fresh conversation [SAFE] ${YELLOW}[c]${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}2)${NC} Claude Code (RESUME) - Continue last session [SAFE] ${YELLOW}[C]${NC}"
    echo -e "${BLUE}├─────────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}3)${NC} OpenCode - Multi-model assistant [INFO] ${YELLOW}[o]${NC}"
    echo -e "${BLUE}├─────────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}4)${NC} Codex CLI (Full-Auto) - Model decides [BALANCED] ${YELLOW}[x]${NC}"
    echo -e "${BLUE}├─────────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}5)${NC} GitHub Copilot - Interactive mode [SAFE] ${YELLOW}[g]${NC}"
    echo -e "${BLUE}├─────────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}6)${NC} Droid (Medium) - Dev operations [BALANCED] ${YELLOW}[d]${NC}"
    echo -e "${BLUE}├─────────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}7)${NC} Qwen (Auto-Edit) - Auto-approve edits [BALANCED] ${YELLOW}[q]${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}8)${NC} Qwen (YOLO) - Auto-approves everything [⚠️ DANGEROUS] ${YELLOW}[Q]${NC}"
    echo -e "${BLUE}├─────────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}9)${NC} Gemini (Auto-Edit) - Auto-approve edits [BALANCED] ${YELLOW}[i]${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}10)${NC} Gemini (YOLO) - Auto-approves everything [⚠️ DANGEROUS] ${YELLOW}[I]${NC}"
    echo -e "${BLUE}├─────────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}11)${NC} Exit ${YELLOW}[e]${NC}"
    echo -e "${BLUE}└─────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "${CYAN}⚙️  Quick Commands:${NC}"
    echo -e "${CYAN}   h)${NC} Help ${YELLOW}[📚]${NC}    ${CYAN}s)${NC} Status ${YELLOW}[📊]${NC}    ${CYAN}c)${NC} Clear last ${YELLOW}[🧹]${NC}"
    echo ""
    echo -e "${CYAN}📋 Enter choice (number or quick key):${NC} \c"
    read -r input

    # Process input - first check for quick keys
    case $input in
        "h"|"H")
            show_help
            continue
            ;;
        "s"|"S")
            show_status
            continue
            ;;
        "c")
            clear_last_selection
            continue
            ;;
        "q"|"Q"|"e"|"E"|11)
            echo -e "${CYAN}👋 Thank you for using AI Launcher!${NC}"
            exit 0
            ;;
        "0")
            # Repeat last selection
            if [ -n "$LAST_CHOICE" ]; then
                choice=$LAST_CHOICE
                echo -e "${CYAN}🔄 Repeating last selection: ${BOLD}$LAST_NAME${NC}"
                sleep 1
            else
                echo -e "${YELLOW}⚠️  No previous selection found.${NC}"
                echo -e "${CYAN}ℹ️  Select an option to make it available for quick repeat.${NC}"
                sleep 2
                continue
            fi
            ;;
        "1"|"2"|"3"|"4"|"5"|"6"|"7"|"8"|"9"|"10"|"11")
            choice=$input
            ;;
        "c"|"C")
            # Quick key for Claude NEW
            choice=1
            ;;
        "C")
            # Quick key for Claude RESUME
            choice=2
            ;;
        "o"|"O")
            # Quick key for OpenCode
            choice=3
            ;;
        "x"|"X")
            # Quick key for Codex
            choice=4
            ;;
        "g"|"G")
            # Quick key for GitHub Copilot
            choice=5
            ;;
        "d"|"D")
            # Quick key for Droid
            choice=6
            ;;
        "q")
            # Quick key for Qwen Auto-Edit (not quit)
            choice=7
            ;;
        "Q")
            # Quick key for Qwen YOLO
            choice=8
            ;;
        "i")
            # Quick key for Gemini Auto-Edit
            choice=9
            ;;
        "I")
            # Quick key for Gemini YOLO
            choice=10
            ;;
        "")
            echo -e "${YELLOW}⚠️  No input received. Please enter a selection.${NC}"
            sleep 1
            continue
            ;;
        *)
            echo -e "${RED}❌ Invalid selection: '${BOLD}$input${NC}${RED}'.${NC}"
            echo -e "${YELLOW}💡 Enter a number (0-11) or a quick key. Type 'h' for help.${NC}"
            sleep 2
            continue
            ;;
    esac

    # Save current selection for next time (except exit)
    if [[ "$choice" != "11" ]]; then
        echo "$choice" > "$LAST_SELECTION_FILE"
    fi

    # Launch selected AI CLI
    case $choice in
        1)
            launch_command claude --verbose --dangerously-skip-permissions --allowedTools serena,npm,git,grep,ssh,curl,perl,python3,mysql,redis-cli,clickhouse-client,make,brew,rsync,tmux,source,/usr/local/bin/playwright
            ;;
        2)
            launch_command claude --verbose --continue --dangerously-skip-permissions --allowedTools serena,npm,git,grep,ssh,curl,perl,python3,mysql,redis-cli,clickhouse-client,make,brew,rsync,tmux,source,/usr/local/bin/playwright
            ;;
        3)
            launch_command opencode
            ;;
        4)
            launch_command codex --full-auto
            ;;
        5)
            launch_command copilot
            ;;
        6)
            launch_command droid exec --auto medium
            ;;
        7)
            launch_command qwen --approval-mode auto-edit
            ;;
        8)
            launch_command qwen --yolo
            ;;
        9)
            launch_command gemini --approval-mode auto_edit
            ;;
        10)
            launch_command gemini --yolo
            ;;
        11)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Invalid selection '$choice'. Please run again and choose 0-11.${NC}"
            sleep 1
            continue
            ;;
    esac

    # If we get here, the exec command probably failed, so continue the loop
    echo -e "${YELLOW}⚠️  Command execution failed or was interrupted.${NC}"
    echo -e "${CYAN}🔄 Returning to main menu in 2 seconds...${NC}"
    sleep 2
done
