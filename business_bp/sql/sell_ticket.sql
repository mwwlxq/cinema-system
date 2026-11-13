UPDATE ticket SET is_sold = true, id_order = %s
WHERE id_ticket = %s AND is_sold = false;