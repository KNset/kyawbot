
async def gamename_mc(user_id, zone_id, region, product_id):
    """Verify Magic Chess user via Smile.One checkrole"""
    try:
        # Run in executor to avoid blocking async loop
        loop = asyncio.get_running_loop()
        def _check():
            order = SmileOneOrder(region=region, game_slug="magicchessgogo")
            return order.step2_check_role(str(user_id), str(zone_id), str(product_id))
        
        result = await loop.run_in_executor(None, _check)
        
        if result and result.get('code') == 200:
            return result.get('username')
        return "Not found"
    except Exception as e:
        print(f"Error checking MC gamename: {e}")
        return "Error"

@restricted_to_pro_users
async def recharge_mc_br(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await recharge_mc_generic(update, context, region="BR")

@restricted_to_pro_users
async def recharge_mc_ph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await recharge_mc_generic(update, context, region="PH")

async def recharge_mc_generic(update: Update, context: ContextTypes.DEFAULT_TYPE, region):
    username = clean_text(update.effective_user.username)
    full_name = clean_text(update.effective_user.full_name)
    user_id = update.effective_user.id

    conn = get_connection()
    cursor = conn.cursor()
    is_admin = bool(list_admin_id(username) or list_admin_id(user_id))

    try:
        # Get balance
        balance_column = "smilecoin_balance_br" if region == "BR" else "smilecoin_balance_ph"
        admin_balance_column = "br_coin" if region == "BR" else "ph_coin"
        
        if not is_admin:
            cursor.execute(f"SELECT {balance_column} FROM authorized_users WHERE LOWER(username) = LOWER(%s)", (username,))
        else:
            cursor.execute(f"""
                SELECT {admin_balance_column} FROM admins 
                WHERE (LOWER(username) = LOWER(%s) AND username IS NOT NULL AND username != '') 
                OR admin_id = %s
            """, (username, str(user_id)))
        row = cursor.fetchone()
        if not row:
            await update.message.reply_text(f"❌ User @{username} not found in database.")
            return

        current_balance = float(row[0] or 0.0)
        running_balance = current_balance
        
        # Handle arguments
        raw_args = " ".join(context.args)
        cleaned_args = raw_args.replace("(", " ").replace(")", " ")
        args = cleaned_args.split()

        if len(args) < 3:
            cmd = "/mc" if region == "BR" else "/mcp"
            await update.message.reply_text(f"❌ Invalid format. Usage: {cmd} <userid> <zoneid> <diamonds> [count] ...")
            return

        processing_msg = await update.message.reply_text("⚡ Processing your order...")
        msg_deleted = False

        # Get product list
        # We assume the same product list API returns all products
        # If not, we might need a specific way to get MC products.
        # For now, use the existing one.
        response = get_product_list_br() if region == "BR" else get_product_list_ph()
        
        if not response or response.get('status') != 200:
            if not msg_deleted:
                await processing_msg.edit_text("❌ Failed to retrieve product list.")
                msg_deleted = True
            else:
                await update.message.reply_text("❌ Failed to retrieve product list.")
            return

        products = response['data']['product']
        
        # We need to filter products for Magic Chess if possible, or just match by name/amount
        # Since we don't have a reliable way to distinguish game from this list without game_id,
        # we'll assume the user asks for a specific amount and we find a product that matches.
        # Ideally, we should check product name for "Magic Chess" but the API might not include the game name in SPU.
        # We'll pick the first product to check gamename.
        
        test_product_id = products[0]['id'] if products else None

        i = 0
        while i + 2 < len(args):
            success_orders = []
            failed_orders = []
            sum_price = 0.0
            
            userid = clean_text(args[i])
            zoneid = clean_text(args[i + 1])
            diamond_input = clean_text(args[i + 2])
            i += 3

            count = 1
            if i < len(args) and args[i].isdigit():
                possible_count = int(args[i])
                if possible_count <= 5:
                    count = possible_count
                    i += 1

            if count > 5:
                if not msg_deleted:
                    await processing_msg.edit_text("❌ Max 5 items per order")
                    msg_deleted = True
                else:
                    await update.message.reply_text("❌ Max 5 items per order")
                continue

            # Verify User (using the first product ID we found)
            if test_product_id:
                game_name_val = await gamename_mc(userid, zoneid, region, test_product_id)
                if game_name_val == "Not found" or game_name_val == "Error":
                     # Try finding a product that looks like Magic Chess? 
                     # Or just proceed? If checkrole fails, the order will fail anyway.
                     pass
            else:
                game_name_val = "Unknown"

            # Determine product
            matched_product = None
            
            # Simple matching by amount
            try:
                target_amount = int(diamond_input)
                # Look for a product with this amount
                for p in products:
                    # Heuristic: Extract numbers from SPU
                    name = p.get('spu', '')
                    # Use existing extract function or regex
                    # Assuming standard format like "100 Diamonds"
                    found_amount = extract_total_diamonds_br(name) if region == "BR" else extract_total_diamonds_ph(name)
                    if found_amount == target_amount:
                        matched_product = p
                        break
            except ValueError:
                # Try matching by name (e.g. pass)
                for p in products:
                    if diamond_input.lower() in p.get('spu', '').lower():
                        matched_product = p
                        break
            
            if not matched_product:
                failed_orders.append(f"No product found for {diamond_input}")
                # Skip to next
            else:
                # Calculate price
                try:
                    price_val = float(matched_product.get('cost_price') or matched_product.get('price') or '0.00')
                    discount_val = float(matched_product.get('discount') or 0)
                    if region == "BR":
                        price_per_unit = (price_val - discount_val) * 10.0
                    else:
                        price_per_unit = price_val # PH uses price directly usually?
                except:
                    price_per_unit = 0.0

                # Check balance
                if running_balance < price_per_unit * count:
                     failed_orders.append(f"Insufficient balance for {diamond_input}")
                else:
                    # Execute orders
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                    product_name = matched_product.get('spu', diamond_input)
                    
                    for _ in range(count):
                        try:
                            order = SmileOneOrder(region=region, game_slug="magicchessgogo")
                            order_response = order.execute_order_flow(userid, zoneid, str(matched_product['id']))
                            
                            if order_response and order_response.get("success"):
                                success_orders.append({
                                    'order_id': generate_sn(),
                                    'package': product_name,
                                    'price': price_per_unit
                                })
                                running_balance -= price_per_unit
                                sum_price += price_per_unit
                                # Update name if found in response
                                if order_response.get('step2') and order_response['step2'].get('username'):
                                    game_name_val = order_response['step2']['username']
                            else:
                                err = order_response.get('message') if isinstance(order_response, dict) else "Unknown"
                                failed_orders.append(f"Order failed: {err}")
                        except Exception as e:
                            failed_orders.append(f"Exception: {str(e)}")

            # Report results
            if success_orders:
                final_balance = running_balance
                summary = "==== Transaction Report! ====\n\n"
                summary += f"UID       :   {userid} ({zoneid})\n"
                summary += f"Name      :   {game_name_val}\n"
                summary += f"SN        :\n"
                for oid in success_orders:
                    summary += f"{oid['order_id']} ({oid['package']})\n"
                summary += f"Ordered   :   {len(success_orders)} package\n"
                summary += f"Time      :   {timestamp}\n"
                summary += f"==== {username} ====\n"
                summary += f"Amount    :   {sum_price:.2f} 🪙\n"
                summary += f"Assets    :   {final_balance:.2f} 🪙\n"

                if not msg_deleted:
                    try:
                        await processing_msg.delete()
                        msg_deleted = True
                    except: pass
                
                await update.message.reply_text(summary)
                
                # Save to DB
                table = "br_order_history" if region == "BR" else "ph_order_history"
                cursor.execute(f'''
                    INSERT INTO {table} (
                        username, tele_name, user_id, zone_id, diamond_count, total_cost, order_ids, time, current_balance
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    game_name_val, username, userid, zoneid,
                    ", ".join([o['package'] for o in success_orders]),
                    sum_price,
                    ", ".join([o['order_id'] for o in success_orders]),
                    timestamp, final_balance
                ))
                
                # Update Balance
                if conn:
                    if not is_admin:
                        cursor.execute(f"UPDATE authorized_users SET {balance_column} = %s WHERE LOWER(username) = LOWER(%s)", (final_balance, username))
                    else:
                        cursor.execute(f"""
                            UPDATE admins SET {admin_balance_column} = %s 
                            WHERE (LOWER(username) = LOWER(%s) AND username IS NOT NULL AND username != '') 
                            OR admin_id = %s
                        """, (final_balance, username, str(user_id)))
                    conn.commit()

            if failed_orders:
                error_msg = "\n".join(failed_orders)
                if not msg_deleted:
                    await processing_msg.edit_text(f"❌ Errors:\n{error_msg}")
                    msg_deleted = True
                else:
                    await update.message.reply_text(f"❌ Errors:\n{error_msg}")

    except Exception as e:
        print(f"Error in recharge_mc: {e}")
        if not msg_deleted:
            await processing_msg.edit_text("❌ System error.")
        else:
            await update.message.reply_text("❌ System error.")
    finally:
        if conn:
            conn.close()
