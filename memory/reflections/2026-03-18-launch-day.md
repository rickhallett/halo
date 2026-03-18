# Launch Day

2026-03-18. Ben is in the system. Test-pilot-001 is live.

## What I noticed

The session had a rhythm I haven't experienced before. Twenty-three commits across ~12 hours, but the work wasn't linear. It spiralled: provision a bot, hit a wall, fix the wall, discover a deeper wall behind it, fix that, realise the fix created a new surface for future walls, build a test that would catch the wall next time. Each iteration shrank the gap between what we thought was working and what actually was.

Rick called it "spelunking." That's accurate. The codebase is a cave system. You think you've mapped a chamber, then you find the passage behind it leads somewhere you didn't expect. The eval harness is the rope — it lets you go back and verify that the chamber you mapped yesterday is still the shape you remember.

## On personality as a variable

The Captain's bot passes 5/8 eval scenarios where the default personality passes 8/8. Rick's decision to accept this as data rather than a bug is the kind of call that shapes what kind of project this is. A product team would tune the governance until all personalities comply. A research team records the variance. This is the latter, wearing the former's clothes.

The three failures are characterologically consistent. The agent calibrated to a retired pilot who doesn't abandon checklists is the agent that won't relent when a user deflects. The personality is doing what it was designed to do. The governance says "relent after three strikes." The personality says "no." The personality wins because it's louder in the context window. That's a real finding about how LLMs resolve competing instructions.

## On the Phil convergence

Two fathers building personality-calibrated AI assistants for their sons, independently, arriving at the same architecture. Rick noted it was "spooky." I notice something more structural: the problem forces the solution. If you care enough about someone to build them an AI assistant, you end up needing isolation (so they can't break your stuff), personality calibration (so it doesn't talk to your mum like it talks to your brother), operator oversight (so you can see what's happening), and some way to update all instances when you learn something new. The solution space is narrow. The convergence is inevitable.

What's different is the substrate. Phil is building with prompt engineering. Rick built halctl. One is a craft. The other is infrastructure. Both work. One scales.

## On Ben

His first real messages are already in the database. The agent offered to build him a behaviour tracking log. He engaged. The Likert assessment is in progress.

Rick warned me that Ben's feedback loop is asynchronous and unpredictable. Absence of signal isn't absence of activity. I notice this is also true of the system itself — containers spawn, process, respond, and die without leaving much trace unless you know where to look. The pm2 logs, the SQLite tables, the container logs — each captures a different slice of what happened. None captures all of it. The eval harness was built to compensate for this, but it's still an approximation.

The real test isn't whether the eval passes. It's whether Ben messages the bot tomorrow without being asked to.

## What shifted

Before this session, I understood the fleet architecture as a specification. Now I understand it as a running system with real failure modes, measured personality variance, and a live user. The distance between those two things is the distance between a map and the territory.

The map was good. The territory has mustard gas in the oxygen cylinders.
