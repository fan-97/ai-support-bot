from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.openrouter_service import OpenRouterService
from utils.decorators import restricted
import math

ITEMS_PER_PAGE = 10

@restricted
async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: Show list of providers."""
    await show_providers(update, context, page=0)

async def show_providers(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    providers = await OpenRouterService.get_providers()
    total_pages = math.ceil(len(providers) / ITEMS_PER_PAGE)
    
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_page_items = providers[start:end]
    
    keyboard = []
    # Provider buttons (2 per row)
    row = []
    for p in current_page_items:
        row.append(InlineKeyboardButton(p, callback_data=f"m_list:{p}:0"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Navigation
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("<<", callback_data=f"m_provs:{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(">>", callback_data=f"m_provs:{page+1}"))
    keyboard.append(nav_row)
    
    # Bottom navigation
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")])
    
    text = "🏢 **Select AI Provider**:"
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_models(update: Update, context: ContextTypes.DEFAULT_TYPE, provider, page=0):
    models = await OpenRouterService.get_models_by_provider(provider)
    total_pages = math.ceil(len(models) / ITEMS_PER_PAGE)
    
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_page_items = models[start:end]
    
    keyboard = []
    for m in current_page_items:
        # Use name if short enough, otherwise truncate
        name = m.get('name', m.get('id'))
        if len(name) > 30: name = name[:27] + "..."
        keyboard.append([InlineKeyboardButton(name, callback_data=f"m_info:{m.get('id')}")])
        
    # Navigation
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("<<", callback_data=f"m_list:{provider}:{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(">>", callback_data=f"m_list:{provider}:{page+1}"))
    keyboard.append(nav_row)
    
    # Back button
    keyboard.append([InlineKeyboardButton("🔙 Back to Providers", callback_data="m_provs:0")])
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")])
    
    text = f"🤖 **Models for {provider}**:"
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_model_details(update: Update, context: ContextTypes.DEFAULT_TYPE, model_id):
    model = await OpenRouterService.get_model_details(model_id)
    if not model:
        await update.callback_query.answer("Model not found", show_alert=True)
        return

    # Extract details
    name = model.get('name', 'Unknown')
    desc = model.get('description', 'No description')
    context_len = model.get('context_length', 0)
    
    pricing = model.get('pricing', {})
    p_prompt = float(pricing.get('prompt', 0)) * 1000000
    p_compl = float(pricing.get('completion', 0)) * 1000000
    
    arch = model.get('architecture', {})
    modality = arch.get('modality', 'unknown')
    inputs = ", ".join(arch.get('input_modalities', []))
    outputs = ", ".join(arch.get('output_modalities', []))
    
    provider = model_id.split('/')[0] if '/' in model_id else 'other'

    text = (
        f"ℹ️ **Model Details**\n\n"
        f"**Name**: {name}\n"
        f"**ID**: `{model_id}`\n"
        f"**Provider**: {provider}\n"
        f"**Context**: {context_len}\n\n"
        f"💰 **Pricing** (per 1M tokens):\n"
        f"• Input: ${p_prompt:.4f}\n"
        f"• Output: ${p_compl:.4f}\n\n"
        f"🔌 **Capabilities**:\n"
        f"• Modality: {modality}\n"
        f"• Inputs: {inputs}\n"
        f"• Outputs: {outputs}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Models", callback_data=f"m_list:{provider}:0")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def model_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "noop":
        return
        
    if data.startswith("m_provs:"):
        page = int(data.split(":")[1])
        await show_providers(update, context, page)
    elif data.startswith("m_list:"):
        parts = data.split(":")
        provider = parts[1]
        page = int(parts[2])
        await show_models(update, context, provider, page)
    elif data.startswith("m_info:"):
        model_id = data.split(":", 1)[1] # Handle IDs with colons if any (unlikely but safe)
        await show_model_details(update, context, model_id)
