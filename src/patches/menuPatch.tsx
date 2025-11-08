//Credit: https://github.com/jessebofill/DeckWebBrowser

import { afterPatch, Dropdown, findInReactTree, FooterLegendProps, getReactRoot } from "@decky/ui"
import { FC, ReactElement, ReactNode, useState } from "react"
import { FaDiscord } from "react-icons/fa"

interface MainMenuItemPropsBase {
    route: string
    label: ReactNode
    onFocus: () => void
    icon?: ReactElement
    onActivate?: () => void
}

type MainMenuItemProps = MainMenuItemPropsBase & FooterLegendProps;

const getReactTree = () => getReactRoot(document.getElementById('root') as any)

export const patchMenu = () => {
    const menuNode = findInReactTree(getReactTree(), (node: { memoizedProps: { navID: string } }) => node?.memoizedProps?.navID == 'MainNavMenuContainer')
    if (!menuNode || !menuNode.return?.type) {
        //namedLogger.log('Failed to find main menu root node.')
        return () => { }
    }
    const orig = menuNode.return.type
    let patchedInnerMenu: any
    const menuWrapper = (props: any) => {
        const ret = orig(props)
        if (!ret?.props?.children?.props?.children?.[0]?.type) {
            //namedLogger.log('The main menu element could not be found at the expected location. Valve may have changed it.')
            return ret
        }
        if (patchedInnerMenu) {
            ret.props.children.props.children[0].type = patchedInnerMenu
        } else {
            afterPatch(ret.props.children.props.children[0], 'type', (_: any, ret: any) => {
                const isMenuItemElt = (e: any) => e.props?.label && e.props.onFocus && e.props.route && e.type?.toString;
                const menuItems = findInReactTree(ret, (node: any[]) => Array.isArray(node) && node.some(isMenuItemElt)) as Array<any>;

                if (!menuItems) {
                    //namedLogger.log('Could not find menu items to patch.')
                    return ret
                }

                const itemIndexes = getMenuItemIndexes(menuItems);
                const menuItem = menuItems.find(isMenuItemElt) as { props: MainMenuItemProps, type: () => ReactElement };

                const newItem =
                    <MenuItemWrapper
                        key={'deckcord'}
                        route={'/discord'}
                        label='Discord'
                        onFocus={menuItem.props.onFocus}
                        useIconAsProp={!!menuItem.props.icon}
                        MenuItemComponent={menuItem.type}
                    />

                const browserPosition = Number.parseInt(localStorage.getItem("DECKCORD_MENU_POSITION") || "3" as string);

                if (browserPosition === 9) menuItems.splice(itemIndexes[itemIndexes.length - 1] + 1, 0, newItem)
                else menuItems.splice(itemIndexes[browserPosition - 1], 0, newItem)

                return ret
            })
            patchedInnerMenu = ret.props.children.props.children[0].type
        }
        return ret
    }
    menuNode.return.type = menuWrapper
    if (menuNode.return.alternate) {
        menuNode.return.alternate.type = menuNode.return.type;
    }

    return () => {
        menuNode.return.type = orig
        menuNode.return.alternate.type = menuNode.return.type;
    }
}

function getMenuItemIndexes(items: any[]) {
    return items.flatMap((item, index) => (item && item.$$typeof && item.type !== 'div') ? index : [])
}

interface MenuItemWrapperProps extends MainMenuItemProps {
    MenuItemComponent: FC<MainMenuItemProps>;
    useIconAsProp: boolean;
}

const MenuItemWrapper: FC<MenuItemWrapperProps> = ({ MenuItemComponent, label, useIconAsProp, ...props }) => {

    const choosePosition: any = new (Dropdown as any)({
        rgOptions: [
            { label: '1', data: 1 },
            { label: '2', data: 2 },
            { label: '3', data: 3 },
            { label: '4', data: 4 },
            { label: '5', data: 5 },
            { label: '6', data: 6 },
            { label: '7', data: 7 },
            { label: '8', data: 8 },
            { label: '9', data: 9 },
        ],
        selectedOption: 1,
        onChange: (data: any) => {
            localStorage.setItem("DECKCORD_MENU_POSITION", data.data);
            patchMenu();
        }
    });

    (props as any)[useIconAsProp ? 'icon' : 'children'] = <FaDiscord />;

    return (
        <MenuItemComponent
            {...props}
            label={'Discord'}
            onSecondaryActionDescription={"Change Position"}
            onSecondaryButton={(_) => choosePosition.ShowMenu()}
        />
    )
}