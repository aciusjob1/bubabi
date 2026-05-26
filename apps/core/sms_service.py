import africastalking
from decouple import config
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """Africa's Talking SMS integration for BUBABI Clan System."""
    
    _initialized = False
    
    @classmethod
    def _init(cls):
        """Initialize Africa's Talking SDK once."""
        if not cls._initialized:
            username = config('AT_USERNAME', default='sandbox')
            api_key = config('AT_API_KEY', default='')
            
            logger.info(f"Initializing Africa's Talking with username: {username}")
            africastalking.initialize(username, api_key)
            cls._initialized = True
    
    @classmethod
    def send(cls, phone_numbers, message):
        """
        Send SMS to Tanzanian phone numbers.
        
        Args:
            phone_numbers: List of phone strings ['0712345678', '+255712345678']
            message: SMS content (keep under 160 chars for single SMS)
        
        Returns:
            API response dict or None if failed
        """
        if not phone_numbers:
            logger.warning("No phone numbers provided")
            return None
        
        cls._init()
        sms = africastalking.SMS
        
        # Format all numbers to +255XXXXXXXXX
        formatted = []
        for num in phone_numbers:
            num = str(num).strip().replace(' ', '').replace('-', '')
            
            if num.startswith('255'):
                num = '+' + num
            elif num.startswith('0'):
                num = '+255' + num[1:]
            elif not num.startswith('+'):
                num = '+255' + num
            
            formatted.append(num)
        
        sender_id = config('AT_SENDER_ID', default='BUBABI')
        
        # In sandbox, add [Test] prefix if not present
        if 'sandbox' in config('AT_USERNAME', default='').lower():
            if 'Test' not in message and 'test' not in message:
                message = f"[Test] {message}"
                logger.info(f"Sandbox mode: Added [Test] prefix")
        
        try:
            logger.info(f"Sending SMS to {len(formatted)} recipients")
            logger.info(f"Message: {message[:50]}...")
            
            response = sms.send(
                message=message,
                recipients=formatted,
                sender_id=sender_id
            )
            
            # Log each recipient's status
            recipients_data = response.get('SMSMessageData', {}).get('Recipients', [])
            for r in recipients_data:
                status = r.get('status')
                number = r.get('number')
                cost = r.get('cost', '0')
                msg_id = r.get('messageId', 'N/A')
                
                if status == 'Success':
                    logger.info(f"✅ {number}: Sent (ID: {msg_id})")
                else:
                    logger.error(f"❌ {number}: Failed - {status}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ SMS sending failed: {str(e)}")
            return None
    
    @classmethod
    def test_connection(cls):
        """Test Africa's Talking API connection."""
        cls._init()
        try:
            account = africastalking.Application
            response = account.fetch_application_data()
            
            user_data = response.get('UserData', {})
            logger.info("✅ Africa's Talking Connected Successfully!")
            logger.info(f"   Username: {user_data.get('username', 'N/A')}")
            logger.info(f"   Balance: {user_data.get('balance', 'N/A')}")
            
            return {
                'success': True,
                'username': user_data.get('username'),
                'balance': user_data.get('balance')
            }
        except Exception as e:
            logger.error(f"❌ Connection failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def send_bulk(cls, clan, message):
        """Send to all active members with phones."""
        from apps.identity.models import Member
        from apps.identity.constants import MemberStatus
        
        phones = list(Member.objects.filter(
            clan=clan,
            status=MemberStatus.ACTIVE
        ).exclude(phone='').values_list('phone', flat=True))
        
        if phones:
            return cls.send(phones, message)
        return None


class BubabiNotifications:
    """Pre-built SMS templates for common clan communications."""
    
    @staticmethod
    def contribution_reminder(contribution):
        """Send payment reminder for a contribution."""
        member = contribution.member
        if not member.phone:
            return None
        
        name = member.person.full_name if member.person else member.email
        message = (
            f"BUBABI: {name}, "
            f"malipo ya TSh {contribution.amount_due:,.0f} "
            f"({contribution.period_label}) yanahitajika kabla ya "
            f"{contribution.due_date.strftime('%d/%m/%Y')}."
        )
        return SMSService.send([member.phone], message)
    
    @staticmethod
    def late_payment_warning(contribution):
        """Send overdue payment warning."""
        member = contribution.member
        if not member.phone:
            return None
        
        name = member.person.full_name if member.person else member.email
        message = (
            f"BUBABI: {name}, "
            f"malipo yako ya TSh {contribution.amount_due:,.0f} "
            f"yamechelewa. Tafadhali lipa haraka kuepuka faini."
        )
        return SMSService.send([member.phone], message)
    
    @staticmethod
    def fine_notification(fine):
        """Notify member about a new fine."""
        member = fine.member
        if not member.phone:
            return None
        
        name = member.person.full_name if member.person else member.email
        message = (
            f"BUBABI: {name}, "
            f"umetozwa faini ya TSh {fine.amount:,.0f} "
            f"kwa: {fine.reason}."
        )
        return SMSService.send([member.phone], message)
    
    @staticmethod
    def loan_status_update(loan):
        """Send loan status notification."""
        member = loan.borrower
        if not member.phone:
            return None
        
        name = member.person.full_name if member.person else member.email
        status = loan.status.lower()
        
        messages_dict = {
            'approved': (
                f"Hongera {name}! "
                f"Mkopo wako wa TSh {loan.amount_approved:,.0f} "
                f"umeidhinishwa."
            ),
            'disbursed': (
                f"BUBABI: {name}, "
                f"TSh {loan.amount_approved:,.0f} imetumwa kwako. "
                f"Rejesha kabla ya {loan.due_date.strftime('%d/%m/%Y')}."
            ),
            'rejected': (
                f"BUBABI: Samahani {name}, "
                f"ombi lako la mkopo halikuidhinishwa. "
                f"Wasiliana na mweka hazina."
            ),
        }
        
        message = messages_dict.get(status, f"BUBABI: Update on your loan application.")
        return SMSService.send([member.phone], message)
    
    @staticmethod
    def meeting_reminder(event, members):
        """Send meeting reminder to multiple members."""
        phones = [m.phone for m in members if m.phone]
        if not phones:
            return None
        
        message = (
            f"BUBABI: Mkutano '{event.title}'\n"
            f"Tarehe: {event.scheduled_at.strftime('%d/%m/%Y %H:%M')}\n"
            f"Mahali: {event.location or 'TBA'}"
        )
        return SMSService.send(phones, message)
    
    @staticmethod
    def announcement_broadcast(announcement, members):
        """Broadcast announcement to all active members."""
        phones = [m.phone for m in members if m.phone]
        if not phones:
            return None
        
        # Truncate message to fit SMS (160 chars)
        max_len = 140  # Leave room for prefix
        content = announcement.content[:max_len]
        if len(announcement.content) > max_len:
            content += "..."
        
        message = f"BUBABI: {announcement.title}\n{content}"
        
        # Send in batches of 10 to avoid rate limiting
        responses = []
        for i in range(0, len(phones), 10):
            batch = phones[i:i+10]
            response = SMSService.send(batch, message)
            responses.append(response)
        
        return responses
    
    @staticmethod
    def bulk_message(clan, title, content):
        """Send bulk message to all active clan members."""
        from apps.identity.models import Member
        from apps.identity.constants import MemberStatus
        
        members = Member.objects.filter(
            clan=clan,
            status=MemberStatus.ACTIVE
        ).exclude(phone='')
        
        phones = [m.phone for m in members]
        if not phones:
            return None
        
        message = f"BUBABI: {title} - {content[:100]}"
        return SMSService.send(phones, message)