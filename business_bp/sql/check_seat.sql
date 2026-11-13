SELECT id_ticket FROM ticket
WHERE id_session = %s AND row_number = %s AND seat_number = %s AND is_sold = false;