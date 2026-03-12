from dotenv import dotenv_values
config = dotenv_values(".env")
users = []
for s in config.get("USER").split(","):
    users.append(int(s))
def check_user(user_id):
    return user_id in users
async def interaction_user(interaction):
    if check_user(interaction.user.id):
        return True
    else:
        await interaction.response.send_message("実行権限がありません",ephemeral=True)
        return False