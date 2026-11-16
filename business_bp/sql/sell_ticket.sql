UPDATE ticket
SET is_sold = true
WHERE id_ticket = %s AND is_sold = false;