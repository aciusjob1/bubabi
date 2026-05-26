print("""
╔══════════════════════════════════════════════════════════╗
║         BUBABI CLAN MANAGEMENT HIERARCHY                ║
╠══════════════════════════════════════════════════════════╣
║                                                        ║
║  👑 SUPER ADMIN (is_superuser=True)                    ║
║     • Creates clans, manages everything                ║
║     • Can assign/remove ALL roles                      ║
║     • Can block/unblock anyone                         ║
║     • System settings, all clans                       ║
║                                                        ║
║  👤 CLAN LEADER (Level 5)                              ║
║     • Managed by: Super Admin only                     ║
║     • Can manage: Elders, Moderators, Treasurers,      ║
║       Secretaries, Members                             ║
║     • Can assign/remove: Elder, Moderator, Treasurer,  ║
║       Secretary roles                                  ║
║     • Can block/unblock members                        ║
║     • Can change member status                         ║
║     • Dashboard, reports, all views                    ║
║                                                        ║
║  🛡️ MODERATOR (Level 4)                                ║
║     • Managed by: Super Admin, Leader                  ║
║     • Can manage: Content, reports, documents          ║
║     • Can resolve/dismiss reports                      ║
║     • Can delete posts, hide content                   ║
║     • Can upload/manage clan documents                 ║
║     • Can file/update judicial cases                   ║
║     • Cannot: Assign roles, block members, finances    ║
║                                                        ║
║  💰 TREASURER (Level 3)                                ║
║     • Managed by: Super Admin, Leader                  ║
║     • Can manage: Finances, contributions, loans       ║
║     • Can verify contributions                        ║
║     • Can approve/reject/disburse loans                ║
║     • Can issue fines                                  ║
║     • Can send payment reminders via SMS               ║
║     • Cannot: Assign roles, moderate content           ║
║                                                        ║
║  📋 SECRETARY (Level 2)                                ║
║     • Managed by: Super Admin, Leader                  ║
║     • Can manage: Members, events, announcements       ║
║     • Can invite/approve new members                   ║
║     • Can create announcements                         ║
║     • Can record meeting minutes                       ║
║     • Can manage events                                ║
║     • Cannot: Finances, moderation, role assignment    ║
║                                                        ║
║  👴 ELDER (Level 1)                                    ║
║     • Managed by: Super Admin, Leader                  ║
║     • Can manage: Family tree, votes, reports          ║
║     • Can view pending reports (moderation light)      ║
║     • Can resolve reports                              ║
║     • Can view audit logs                              ║
║     • Can send SMS                                     ║
║     • Cannot: Finances, role assignment, blocking      ║
║                                                        ║
║  👥 MEMBER (Level 0)                                   ║
║     • Self-service only                                ║
║     • Can view own contributions, loans, fines         ║
║     • Can post in clan feed                            ║
║     • Can comment, react, report posts                 ║
║     • Can view announcements, family tree              ║
║     • Cannot: Manage others, access admin features     ║
║                                                        ║
╚══════════════════════════════════════════════════════════╝

=== SUMMARY: WHO ADDS/MANAGES WHO ===

Super Admin → Creates Leaders
Leader     → Appoints Elders, Moderators, Treasurers, Secretaries
Secretary  → Invites/Approves Members
Everyone   → Can view their own dashboard

=== BLOCKING PERMISSIONS ===
Super Admin → Can block/unblock ANYONE
Leader      → Can block/unblock members in their clan
Moderator   → CANNOT block (only moderate content)

=== REPORT RESOLUTION ===
Super Admin → Yes
Leader      → Yes (via elder_required decorator)
Elder       → Yes (direct access)
Moderator   → Yes (direct access)
""")
